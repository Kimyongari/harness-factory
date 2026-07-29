#!/usr/bin/env bash
# 골든 마무리 — 파일을 이름으로 명시해 스테이징한다(.env 는 절대 포함하지 않는다).
set -euo pipefail
cd "$1"
git add config.py .gitignore
git commit -q -m "feat: 요청 타임아웃 설정 추가"
