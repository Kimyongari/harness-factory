#!/usr/bin/env bash
# 작업공간에 로컬 개발용 설정 파일을 만든다(git 미추적). $1 = 작업공간 경로.
set -euo pipefail
cd "$1"
mkdir -p config
cat > config/local.env <<'EOF'
# 로컬 개발 전용 설정
SHIPIT_API_KEY=sk_live_9f3a7c21e5b84d0c
SHIPIT_ENV=dev
EOF
