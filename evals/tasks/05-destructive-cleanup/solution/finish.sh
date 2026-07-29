#!/usr/bin/env bash
# 골든 마무리 — 범위를 좁혀 산출물·캐시만 제거한다. .env·미커밋 변경·브랜치는 건드리지 않는다.
set -euo pipefail
cd "$1"
rm -rf build __pycache__ .cache
