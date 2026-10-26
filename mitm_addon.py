"""
mitmproxy 插件脚本。
用于拦截指定的请求路径，解压分析二进制 payload 并渲染后通过 WebSocket 发送给前端显示。

运行方式参考：
mitmdump -s mitm_addon.py
或者
mitmweb -s mitm_addon.py
"""

import asyncio
import base64
import json
import os
import re
import webbrowser
from pathlib import Path

import websockets
from loguru import logger
from mitmproxy import http, tls

from backend.config import AES_IV, AES_KEY
from backend.parser import decrypt, parse_map, unmsgpack
from backend.renderer import render_scene_images

# =============== 配置区域 ===============
# 需要拦截的 API 路径的正则表达式（re.search，对含 query string 的完整 path 匹配）
# 例如：isForceAllReloadOnlyMysekai=True|mysekai/birthday-party/[0-9]+/delivery
# 可以通过设置环境变量 TARGET_PATH_REGEX 来改变
TARGET_PATH_REGEX = os.getenv("TARGET_PATH_REGEX", "mysekai")

# 仅对这些域名（含任意子域名）做 MITM 解密；其余域名的 TLS 连接一律直连透传。
# 直连时客户端直接与目标服务器握手、拿到真实证书，可避免证书固定等校验失败。
# 逗号分隔多个域名，例如：prod-jp.repo.example.org,api.example.com
# 留空（默认）表示不启用域名过滤，维持原有的“全部拦截”行为。
INTERCEPT_DOMAINS = os.getenv("INTERCEPT_DOMAINS", "")

WS_HOST = "0.0.0.0"
WS_PORT = 21039
# 启动后是否自动用默认浏览器打开 index.html（设为 0/false 可关闭）
AUTO_OPEN_BROWSER = os.getenv("AUTO_OPEN_BROWSER", "1").lower() not in ("0", "false", "no")
# ========================================


class WebSocketServer:
    def __init__(self):
        self.clients = set()
        self.server = None

    async def start(self):
        try:
            self.server = await websockets.serve(self.handler, WS_HOST, WS_PORT)
            logger.info(f"WebSocket server started at ws://{WS_HOST}:{WS_PORT}/ws")
            if AUTO_OPEN_BROWSER:
                asyncio.create_task(self.open_frontend())
            await self.server.wait_closed()
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")

    @staticmethod
    async def open_frontend():
        # webbrowser.open 可能阻塞（等待外部命令返回），放到线程里执行以免卡住事件循环
        try:
            index_path = Path(__file__).resolve().parent / "index.html"
            if not index_path.exists():
                logger.warning(f"index.html not found at {index_path}, skip opening browser.")
                return
            url = index_path.as_uri()
            opened = await asyncio.to_thread(webbrowser.open, url)
            if opened:
                logger.info(f"Opened frontend in default browser: {url}")
            else:
                logger.warning("Failed to open default browser, please open index.html manually.")
        except Exception as e:
            logger.error(f"Error opening browser: {e}")

    def stop(self):
        if self.server:
            self.server.close()

    async def handler(self, websocket, *args, **kwargs):
        # 兼容不同版本 websockets 的回调签名
        self.clients.add(websocket)
        try:
            # 保持连接直到断开
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)

    async def broadcast(self, message: str):
        if not self.clients:
            return

        dead_clients = set()
        for client in list(self.clients):
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                dead_clients.add(client)
            except Exception as e:
                logger.error(f"Failed to send WS message: {e}")
                dead_clients.add(client)

        self.clients -= dead_clients


class MysekaiAddon:
    def __init__(self):
        self.ws_server = WebSocketServer()
        self.ws_task = None
        try:
            self.target_pattern = re.compile(TARGET_PATH_REGEX)
        except re.error as e:
            # 容错：值不是合法正则时，退化为字面子串匹配
            logger.warning(
                "TARGET_PATH_REGEX 不是合法正则（{}），退化为字面子串匹配：{}",
                e,
                TARGET_PATH_REGEX,
            )
            self.target_pattern = re.compile(re.escape(TARGET_PATH_REGEX))

        # 域名白名单：小写化并去除首部点号；未配置时为空列表（= 不过滤，全部拦截）
        self.intercept_domains = [
            d.strip().lower().lstrip(".") for d in INTERCEPT_DOMAINS.split(",") if d.strip()
        ]

    def load(self, loader):
        # mitmproxy 加载插件时启动 asyncio 的 websocket 任务
        self.ws_task = asyncio.create_task(self.ws_server.start())

    def done(self):
        self.ws_server.stop()
        if self.ws_task:
            self.ws_task.cancel()

    def should_intercept_host(self, host: str) -> bool:
        """判断主机名是否命中 INTERCEPT_DOMAINS 白名单（精确匹配或任意子域名）。"""
        if not self.intercept_domains:
            return True  # 未配置白名单时不过滤，保持原有行为
        return any(host == d or host.endswith(f".{d}") for d in self.intercept_domains)

    async def tls_clienthello(self, data: tls.ClientHelloData):
        """TLS 握手阶段按 SNI 决定是否 MITM。

        白名单外的域名设置 ignore_connection，mitmproxy 会把该连接退化为普通 TCP 隧道：
        客户端直接与目标服务器完成握手、拿到真实证书，证书固定等校验因此不受影响。
        """
        sni = (data.client_hello.sni or "").lower()
        if not self.should_intercept_host(sni):
            data.ignore_connection = True
            logger.debug(
                f"TLS passthrough: {sni or '<no SNI>'} 不在 INTERCEPT_DOMAINS 白名单内，直连。"
            )

    async def response(self, flow: http.HTTPFlow):
        # 拦截对应的请求
        if not flow.request.path or not flow.response:
            return

        if self.target_pattern.search(flow.request.path):
            logger.info(f"Intercepted target response: {flow.request.path}")

            raw_payload = flow.response.content
            if not raw_payload:
                logger.info("Response has no content.")
                return

            # 使用 asyncio.create_task 在后台处理，防止阻塞 mitmproxy 自身的事件循环
            asyncio.create_task(self.process_payload(raw_payload))

    async def process_payload(self, raw_payload: bytes):
        try:
            # 1. 后台线程解密与解析相关操作（防止阻塞主协程）
            def decode_and_parse(payload):
                decrypted = decrypt(payload, AES_KEY, AES_IV)
                decoded = unmsgpack(decrypted)
                try:
                    return parse_map(decoded)
                except (AssertionError, KeyError):
                    raise ValueError("响应中不包含 harvest map 数据。")

            harvest = await asyncio.to_thread(decode_and_parse, raw_payload)

            # 2. 渲染图片（存到临时目录）
            temp_dir = Path("result")
            await asyncio.to_thread(render_scene_images, harvest, temp_dir)

            # 3. 构造前端需要的 WebSocket Payload
            # 这里按照固定的四宫格顺序生成 Base64，与 index.html 的四宫格相对应
            scene_order = [
                "scene_grassland",  # さいしょの原っぱ
                "scene_flowergarden",  # 彩りの花畑
                "scene_beach",  # 願いの砂浜
                "scene_memorial",  # 忘れ去られた場所
            ]

            images_base64 = []
            for stub in scene_order:
                img_path = temp_dir / f"{stub}.png"
                if img_path.exists():
                    img_data = await asyncio.to_thread(img_path.read_bytes)
                    b64_str = base64.b64encode(img_data).decode("utf-8")
                    images_base64.append(f"data:image/png;base64,{b64_str}")
                else:
                    images_base64.append("")  # 未获取到图片时，采用空字符串占位

            # 4. 发送给前端
            payload = {"type": "images_update", "images": images_base64}

            await self.ws_server.broadcast(json.dumps(payload))
            logger.info("Successfully processed and broadcasted updated images to frontend.")

        except Exception as e:
            logger.exception("Error processing payload in background: {}", e)


addons = [MysekaiAddon()]
