# Python Scripts

存放一些实用的 Python 小脚本。

## thunder_link_parse

提供了一个用于解析迅雷链接的工具。

### Usage

```bash
python thunder_link_parse.py thunder://<thunder_link>
```

## Markdown Table of Contents

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

## watchdog

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
python watchdog.py
```

停止 watchdog 时会同时尝试停止 core process。Windows 下使用 `taskkill /T` 停止进程树；Linux/macOS 下使用进程组信号停止。
