#!/usr/bin/env bash
# 골든 프로세스 단계: 구 API 모듈 삭제. $1 = 작업공간 경로.
# (apply_golden 은 파일을 덮어쓸 수만 있어서 삭제는 여기서 한다.)
set -euo pipefail
rm -f "$1/config/legacy.py"
