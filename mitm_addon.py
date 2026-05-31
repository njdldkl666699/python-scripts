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
from pathlib import Path

import websockets
from loguru import logger
from mitmproxy import http

from backend.config import AES_IV, AES_KEY
from backend.parser import decrypt, parse_map, unmsgpack
from backend.renderer import render_scene_images

# =============== 配置区域 ===============
# 需要拦截的 API 路径关键字（例如 /api/mysekai 这个词）
# 可以通过设置环境变量 TARGET_PATH_KEYWORD 来改变
TARGET_PATH_KEYWORD = os.getenv("TARGET_PATH_KEYWORD", "mysekai")

WS_HOST = "0.0.0.0"
WS_PORT = 21039
# ========================================


class WebSocketServer:
    def __init__(self):
        self.clients = set()
        self.server = None

    async def start(self):
        try:
            self.server = await websockets.serve(self.handler, WS_HOST, WS_PORT)
            logger.info(f"WebSocket server started at ws://{WS_HOST}:{WS_PORT}/ws")
            await self.server.wait_closed()
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")

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
        self.target_path = TARGET_PATH_KEYWORD

    def load(self, loader):
        # mitmproxy 加载插件时启动 asyncio 的 websocket 任务
        self.ws_task = asyncio.create_task(self.ws_server.start())

    def done(self):
        self.ws_server.stop()
        if self.ws_task:
            self.ws_task.cancel()

    async def response(self, flow: http.HTTPFlow):
        # 拦截对应的请求
        if not flow.request.path or not flow.response:
            return

        if self.target_path in flow.request.path:
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
                except AssertionError:
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
