# pjsk-mysekai-xray

用于解析 Project Sekai Mysekai 响应数据的命令行脚本与实时拦截展示工具。

这个仓库当前提供的核心能力有两项：

1. **静态解析**：读取加密的响应 payload，使用 `.env` 中配置的 AES 参数解密，并把采集点掉落信息整理成 JSON 或渲染成 PNG 图片。
2. **实时代理拦截**：内置 `mitmproxy` 插件，在运行代理时自动拦截 API 数据并在前端界面实时呈现掉落分布。

## 功能概览

- 支持从抓包文件或标准输入读取加密响应并解析
- 支持提取并渲染特定场景的标注图 (PNG)
- **mitmproxy 插件级拦截**：在手机或本机的抓包环境内实时解密响应并自动推送
- **WebSocket 实时展示界面**：纯静态前端，随时预览最新地图刷新情况

支持渲染的场景：

- さいしょの原っぱ
- 願いの砂浜
- 彩りの花畑
- 忘れ去られた場所

## 目录说明

- `main.py`：单次离线解析的主脚本入口
- `mitm_addon.py`：mitmproxy 对应的实时拦截处理插件
- `index.html`：本地简易 WebSocket 前端可视化界面
- `ws_protocol.md`：WebSocket 的前端后台交互协议格式
- `backend/`：核心解析、AES解密、绘图渲染逻辑
- `img/`：场景底图
- `icon/Texture2D/`：游戏掉落资源小图标

---

## 环境与依赖配置

### 环境要求

```bash
uv sync
```

### 环境变量

脚本启动时会从 `.env` 中读取 `AES_KEY` 和 `AES_IV`。如果缺失，程序无法解密网络数据。

在项目根目录创建 `.env`：

```env
AES_KEY=your_aes_key
AES_IV=your_aes_iv
```

---

## 运行模式一：实时拦截与可视化 (mitmproxy 插件)

利用内置代理脚本，可在触发游戏数据的瞬间解密并渲染出来。

1. **启动代理服务**
   请在终端启动 mitmdump（或 mitmweb）并挂上脚本：
   
   ```bash
   mitmdump -s mitm_addon.py
   ```
   
   启动后，核心代理将开启（默认端口 `8080`），同时启动一个内部 WebSocket 数据推送服务（默认端口 `21039`）。

2. **启动前端监控**
   无需构建工具，双击直接在浏览器中打开项目根目录下的 `index.html`。
   显示“已连接到服务器”即代表联通。

3. **抓包测试**
   配置好手机或电脑环境的代理（指向 `127.0.0.1:8080`，并安装信任了 mitm 证书）。当您在游戏中获取/刷新数据，后端插件将捕获包含 `mysekai`（可通过改环境变量 `TARGET_PATH_KEYWORD` 配置）过滤路径的 API。随后进行自动流式解密及绘图，再通过 WebSocket 发送回前端，此时网页端的 4 张场景掉落图就会被瞬间更新覆盖。

---

## 运行模式二：命令行静态离线解析 (main.py)

如果您已经提前获取到了响应体抓包文件，也可以使用此命令行跑批入口。

### 输入形式

#### 1. 从响应文件读取

```bash
python main.py --response-file response_mkcn-prod-public-60001-1.dailygn.com_mysekai
```

#### 2. 从标准输入管道读取

```bash
cat encrypted.bin | python main.py
```

### 提取并解析 JSON 结构

默认情况下，该行为会向控制台输出提纯和聚合后的采集掉落 JSON 数据：

```json
{
  "さいしょの原っぱ": [
    {
      "location": [1, -14],
      "fixtureId": 1001,
      "reward": {
        "mysekai_material": {
          "1": 6,
          "2": 1
        }
      }
    }
  ]
}
```

（可以通过增加 `--dump-decrypted` 提供调试输出或者修改 `--compact` 改变排版）。

### 静默场景渲染（替代打印）

利用 `--render-scenes` 指定输出目录可以直接进行离线渲染，取代打印 JSON 数据：

```bash
python main.py --response-file response.bin --render-scenes result
```

执行后将解析每个点的二维坐标，标记在预设的底图上，并在 `result/` 保存 PNG 图片格式。

---

## 备注与注意事项

- 场景底图定义、图标映射和稀有物颜色等阈值信息目前分离存放在 `backend/config.py` 中。
- 本插件基于当前的特定游戏业务 API 的返回结构编写。如果未来 API Payload 发生字段异动，请对应的进入 `backend/parser.py` 和 `backend/structs.py` 中去跟随调整解析模型。