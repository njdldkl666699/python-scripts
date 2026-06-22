#!/usr/bin/env bash
set -euo pipefail

RESPONSE_FILE="$HOME/storage/downloads/Reqable/response_mkcn-prod-public-60001-1.dailygn.com_mysekai"
OUTPUT_DIR="$HOME/storage/dcim/pjsk-mysekai"
rm -f "$OUTPUT_DIR"/*.png
cd python-scripts
uv run main.py --response-file "$RESPONSE_FILE" --render-scenes "$OUTPUT_DIR"
rm -f "$RESPONSE_FILE"
cd ..