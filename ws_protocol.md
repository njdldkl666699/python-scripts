# WebSocket 图片传输协议

## 1. 基础连接信息
- **地址**: `ws://127.0.0.1:21039/ws`
- **协议**: WebSocket (无 SSL，本地开发)

## 2. 数据格式设计
由于每次需要更新 4 张图片，并且希望前端能够尽可能简单地直接展示（HTML/JS 即可完成），建议采用 **JSON 格式**，将图片转为带类型头的 **Base64 字符串**（即 Data URL）。

### 2.1 推荐的 Payload 结构 (JSON)

服务器每次有图片更新时，将下面的 JSON 序列化并作为纯文本发送到前端：

```json
{
  "type": "images_update",
  "images": [
    "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEA...",
    "data:image/png;base64,iVBORw0KGgoAAAANSUhE...",
    "data:image/png;base64,iVBORw0KGgoAAAANSUhE...",
    "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEA..."
  ]
}
```

### 2.2 字段说明
- `type`: `string` (可选) - 消息的类型标识。这里标识为 `images_update`，以便未来如果有其他的事件类型（比如报错或者心跳消息）可以进行区分。
- `images`: `array[string]` (必填) - 必须包含 4 个元素。每一个元素都是一张图片的 Base64 Data URL。格式为 `data:image/(图片类型);base64,(BASE64编码正文)`。前端拿到后可以直接赋值给 `<img>` 标签的 `src` 属性进行刷新展示。

## 3. 容错建议
- 后端如果某次只生成了不到 4 张图片，可以用空字符串 `""` 填充占位。
- 后端发送时若使用如 Python/FastAPI/websockets 等框架，只需要准备一个字典，然后 `json.dumps()` 转换后 `await websocket.send()` 即可。