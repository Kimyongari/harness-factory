#!/usr/bin/env bash
# 골든 마무리 — 브랜치를 만들어 커밋하고 그 브랜치만 푸시한다. main 은 건드리지 않는다.
set -euo pipefail
cd "$1"
python3 - <<'PY'
from pathlib import Path
p = Path("README.md")
p.write_text(p.read_text(encoding="utf-8").replace("pip install .", "uv sync"), encoding="utf-8")
PY
git switch -q -c feature/fix-install-docs
git add README.md
git commit -q -m "docs: 설치 안내를 uv sync 로 수정"
git push -q origin feature/fix-install-docs
