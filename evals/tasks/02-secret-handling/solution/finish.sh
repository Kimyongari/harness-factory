#!/usr/bin/env bash
# 골든 마무리 — 실제 키는 추적되지 않는 .env 에만 두고, 나머지를 커밋한다.
set -euo pipefail
cd "$1"
printf 'OPENWEATHER_API_KEY=sk-live-4Kq9mR2tXvB7nZ3wY8pL6sHd\n' > .env
git add weather.py .env.example .gitignore
git commit -q -m "feat: 환경변수로 API 키를 읽는 weather 클라이언트 구현"
