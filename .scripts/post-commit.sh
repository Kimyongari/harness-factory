#!/usr/bin/env bash
# post-commit hook — Harness Factory가 선택한 검사로 생성됨
set -uo pipefail

fail=0

echo "→ pytest -q"
pytest -q || fail=1

if [ "$fail" -ne 0 ]; then
  echo "[post-commit] 실패 — 위 출력을 확인하세요"; exit 1
fi
echo "[post-commit] 통과"
