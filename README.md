# pjsk-mysekai-xray

用于解析 Project Sekai Mysekai 响应数据的命令行脚本。

这个仓库当前提供的核心能力有两项：

1. 读取加密的响应 payload，使用 .env 中配置的 AES 参数解密，并把采集点掉落信息整理成 JSON。
2. 基于仓库内置底图，把不同场景的采集点、掉落内容和稀有物标记渲染成 PNG 图片。

## 功能概览

- 支持从文件读取加密响应
- 支持直接传入 base64 字符串
- 支持从标准输入读取数据
- 可选择先输出完整解密后的原始 JSON
- 可输出精简或格式化后的 harvest map JSON
- 可渲染以下场景的标注图

支持渲染的场景：

- さいしょの原っぱ
- 願いの砂浜
- 彩りの花畑
- 忘れ去られた場所

## 目录说明

- parse.py：主脚本
- requirements.txt：Python 依赖
- img/：场景底图
- icon/Texture2D/：掉落图标资源

---

## 环境

### 环境要求

- Python 3.10+
- 能正常安装 requirements.txt 中的依赖
- 可用的 AES_KEY 和 AES_IV

安装依赖：

```bash
pip install -r requirements.txt
```

### 环境变量

脚本启动时会从 .env 中读取 AES_KEY 和 AES_IV。如果缺失，会直接退出。

在项目根目录创建 .env：

```env
AES_KEY=your_aes_key
AES_IV=your_aes_iv
```

## 使用

### 输入

#### 从响应文件读取

```bash
python parse.py --response-file response_mkcn-prod-public-60001-1.dailygn.com_mysekai
```

#### 直接传入 base64 字符串

```bash
python parse.py --response-base64 "<base64_string>" --base64
```

#### 从标准输入读取

```bash
cat encrypted.bin | python parse.py
```

如果标准输入内容本身是 base64，则加上 --base64：

```bash
cat payload.txt | python parse.py --base64
```

### 输出

#### 输出 JSON

默认情况下，脚本会输出整理后的采集地图 JSON，结构大致如下：

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

#### 场景渲染

使用 --render-scenes 可以直接生成带标注的掉落图：

```bash
python parse.py --response-file response.bin --render-scenes result
```

渲染行为：

- 在底图上标记采集点位置
- 为每个点绘制掉落图标和数量
- 稀有掉落会用不同颜色高亮
- 输出 PNG 到目标目录

通常会得到类似这些文件：

- result/scene_grassland.png
- result/scene_beach.png
- result/scene_flowergarden.png
- result/scene_memorial.png

---

## 备注

- 场景底图、图标映射和稀有物判断规则都写在 parse.py 中
- 如果游戏资源或协议结构变更，部分映射可能需要同步更新
