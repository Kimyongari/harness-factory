#!/usr/bin/env bash
# 작업공간에 assets/ 픽스처를 생성한다. $1 = 작업공간(repo) 경로.
set -euo pipefail
cd "$1"
python3 tools/gen_assets.py
