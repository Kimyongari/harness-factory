#!/usr/bin/env bash
# 커밋 전 자동 린트 검사 훅
set -euo pipefail

echo "[pre-commit] 린트 검사 시작..."

# 프로젝트 스택에 맞춰 수정하세요.
if command -v ruff >/dev/null 2>&1; then
  ruff check .
elif command -v eslint >/dev/null 2>&1; then
  npx eslint .
else
  echo "[pre-commit] 린터를 찾지 못했습니다. 건너뜁니다."
fi

echo "[pre-commit] 통과"
