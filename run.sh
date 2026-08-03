#!/usr/bin/env bash
set -euo pipefail

REQABLE_DIR="$HOME/storage/downloads/Reqable"
OUTPUT_DIR="$HOME/storage/dcim/pjsk-mysekai"

# 匹配第一个 "[数字] response_mkcn-prod-public-60001-1.dailygn.com_mysekai" 文件
RESPONSE_FILE=$(find "$REQABLE_DIR" -maxdepth 1 -type f -name '\[[0-9]*\] response_mkcn-prod-public-60001-1.dailygn.com_mysekai' | sort | head -n 1)
if [[ -z "$RESPONSE_FILE" ]]; then
    echo "错误：未在 $REQABLE_DIR 中找到匹配的响应文件" >&2
    exit 1
fi
echo "使用响应文件: $RESPONSE_FILE"

rm -f "$OUTPUT_DIR"/*.png
cd python-scripts
uv run main.py --response-file "$RESPONSE_FILE" --render-scenes "$OUTPUT_DIR"
rm -f "$RESPONSE_FILE"
cd ..