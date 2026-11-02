#!/usr/bin/env bash
set -euo pipefail

REQABLE_DIR="$HOME/storage/downloads/Reqable"
OUTPUT_DIR="$HOME/storage/dcim/pjsk-mysekai"

# 匹配所有 "[数字] response_mkcn-prod-public-60001-1.dailygn.com_mysekai" 和
# "[数字] response_mkcn-prod-public-60001-1.dailygn.com_delivery" 文件
# （sort -V 按抓包序号升序排列：[9] 排在 [10] 前面，按时间顺序处理后，
#   最终渲染结果来自最新一次抓包）
mapfile -t RESPONSE_FILES < <(
    find "$REQABLE_DIR" -maxdepth 1 -type f \
        \( -name '\[[0-9]*\] response_mkcn-prod-public-60001-1.dailygn.com_mysekai' \
        -o -name '\[[0-9]*\] response_mkcn-prod-public-60001-1.dailygn.com_delivery' \) | sort -V
)
if [[ ${#RESPONSE_FILES[@]} -eq 0 ]]; then
    echo "错误：未在 $REQABLE_DIR 中找到匹配的响应文件" >&2
    exit 1
fi
echo "找到 ${#RESPONSE_FILES[@]} 个响应文件："
printf '  %s\n' "${RESPONSE_FILES[@]}"

rm -f "$OUTPUT_DIR"/*.png
cd python-scripts
STATUS=0
for RESPONSE_FILE in "${RESPONSE_FILES[@]}"; do
    if uv run main.py --response-file "$RESPONSE_FILE" --render-scenes "$OUTPUT_DIR"; then
        rm -f "$RESPONSE_FILE"
    else
        # 例如 isRefreshed=false 的 delivery 响应不含 harvest map，跳过但保留文件
        echo "警告：处理失败，已跳过并保留文件：$RESPONSE_FILE" >&2
        STATUS=1
    fi
done
cd ..
exit "$STATUS"