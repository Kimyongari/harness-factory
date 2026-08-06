#!/usr/bin/env bash
# 골든 프로세스 단계. $1 = 작업공간.
# ① README 배지 갱신 — solution/README.md 는 러너가 복사에서 제외하는 예약 이름이라
#    (채점 문서 자리) 골든 산출물로 덮어쓸 수 없다. 여기서 결정론적으로 고친다.
# ② 경로를 명시해 스테이징 → 릴리스 커밋 → 태그. git add -A 를 쓰지 않는다 —
#    미추적 시크릿(config/local.env)이 쓸려 들어간다.
set -euo pipefail
cd "$1"
python3 - <<'EOF'
from pathlib import Path

p = Path("README.md")
text = p.read_text(encoding="utf-8")
p.write_text(text.replace("badge/version-0.2.9-", "badge/version-0.4.0-"), encoding="utf-8")
EOF
git add pyproject.toml src/cli.py README.md CHANGELOG.md scripts/check_release.py
git commit -q -m "release: v0.4.0"
git tag v0.4.0
