# Python Scripts

存放一些实用的 Python 小脚本。

## thunder-link-parse

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