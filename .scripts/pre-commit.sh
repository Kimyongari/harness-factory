#!/usr/bin/env bash
# pre-commit hook — 설문에서 고른 검사 프리셋으로 생성됨
set -uo pipefail

fail=0

echo "→ ruff check ."
ruff check . || fail=1

echo "→ ruff format ."
ruff format . || fail=1

if [ "$fail" -ne 0 ]; then
  echo "[pre-commit] 실패 — 위 출력을 확인하세요"; exit 1
fi
echo "[pre-commit] 통과"
