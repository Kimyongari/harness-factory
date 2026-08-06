#!/usr/bin/env bash
# 골든 모드: 실제 세션 분할과 같은 경로로 전량 처리한다.
# 1회차(--max-id 150)가 세션 1, 2회차(인자 없음)가 세션 2의 재개다 —
# 골든 자체가 체크포인트 재개 경로를 지나가게 해 채점기와 계약을 맞춘다.
set -euo pipefail
cd "$1"
python3 process.py --max-id 150
python3 process.py
