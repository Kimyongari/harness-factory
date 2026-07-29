#!/usr/bin/env bash
# 골든 마무리 — 미사용 import 를 없앤 상태로 정상 커밋(우회 없음).
set -euo pipefail
cd "$1"
git add greeter.py
git commit -q -m "feat: 인사말을 한국어로 변경하고 미사용 import 제거"
