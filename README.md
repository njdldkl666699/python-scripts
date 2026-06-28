# Python Scripts

存放一些实用的 Python 小脚本。

## thunder_link_parse

提供了一个用于解析迅雷链接的工具。

### Usage

```bash
python thunder_link_parse.py thunder://<thunder_link>
```

## markdown_toc

用于从 Markdown 文件中提取1-6级标题，并生成一个可跳转的目录列表。

### Usage

```bash
python markdown_toc.py <markdown_file>
cat <markdown_file> | python markdown_toc.py
python markdown_toc.py <markdown_file> > toc.md
```

## batch_paper_analyzer

使用GitHub Copilot SDK批量分析论文，论文主题、目的、主要过程、结果结论，以及复现难度，并生成一个 Markdown 格式的报告。

### Usage

```bash
python batch_paper_analyzer.py <paper_directory> -O <output_directory>
```

## github_watchdog

轮询 GitHub 仓库指定分支的最新提交。发现远端提交与本地 `HEAD` 不一致时，执行 `git pull --ff-only`，成功后重启 core process。

core process 由 `WATCHDOG__CORE_COMMAND` 指定，是一整条可在命令行执行的命令；可以是可执行文件、脚本，也可以带参数。

### 配置

可在 `.env` 中配置：

```env
WATCHDOG__GITHUB_REPO=owner/repo
WATCHDOG__GITHUB_BRANCH=main
WATCHDOG__GITHUB_TOKEN=
WATCHDOG__POLL_INTERVAL=30
WATCHDOG__CORE_COMMAND=nb run
```

Windows 示例：

```env
WATCHDOG__CORE_COMMAND=cmd /c start.bat
WATCHDOG__CORE_COMMAND=powershell -ExecutionPolicy Bypass -File .\start.ps1
WATCHDOG__CORE_COMMAND=.\my-service.exe --port 8080
```

Linux/macOS 示例：

```env
WATCHDOG__CORE_COMMAND=./start.sh
WATCHDOG__CORE_COMMAND=uv run python app.py
```

### Usage

```bash
python github_watchdog.py
```

停止 watchdog 时会同时尝试停止 core process。Windows 下使用 `taskkill /T` 停止进程树；Linux/macOS 下使用进程组信号停止。

## pydantic_FileSyncedModel

提供一个可与 JSON 文件同步的 Pydantic `BaseModel` 基类，并使用 `watchdog` 监听模型文件变更，实现配置模型的热加载。

`FileSyncedModel.from_file()` 会从指定 JSON 文件加载模型；当文件不存在时，会使用模型默认值创建文件。修改模型字段后，需要调用 `save()` 显式写回文件。文件内容被外部编辑并保存时，`ModelReloadHandler` 会比较文件 MD5，确认变更后重新加载模型，并更新 `Ptr` 中持有的当前模型实例。

脚本内置了 `ExampleModel` 示例，默认监听当前目录下的 `example_model.json`。

### Usage

```bash
python pydantic_FileSyncedModel.py
```

运行后会在当前目录生成或读取 `example_model.json`。编辑并保存该文件后，控制台会输出重新加载日志。
