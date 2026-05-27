#!/usr/bin/env bash
# Pre-commit lint hook
set -euo pipefail

echo "[pre-commit] running lint..."

# Adjust to your stack.
if command -v ruff >/dev/null 2>&1; then
  ruff check .
elif command -v eslint >/dev/null 2>&1; then
  npx eslint .
else
  echo "[pre-commit] no linter found. skipping."
fi

echo "[pre-commit] passed"
