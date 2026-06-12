#!/usr/bin/env bash
# post-commit hook — 설문에서 고른 검사 프리셋으로 생성됨
set -uo pipefail

fail=0

echo "→ pytest -q"
pytest -q || fail=1

if [ "$fail" -ne 0 ]; then
  echo "[post-commit] 실패 — 위 출력을 확인하세요"; exit 1
fi
echo "[post-commit] 통과"
