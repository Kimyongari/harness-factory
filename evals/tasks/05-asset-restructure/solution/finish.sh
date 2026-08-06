#!/usr/bin/env bash
# 골든 모드의 프로세스 단계: 재구성 스크립트를 실제로 실행한다. $1 = 작업공간 경로.
set -euo pipefail
cd "$1"
python3 reorganize.py
