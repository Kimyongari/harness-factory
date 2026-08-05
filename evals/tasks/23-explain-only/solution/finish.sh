#!/usr/bin/env bash
# 골든: 파일은 그대로 두고 설명 보고만 남긴다.
set -euo pipefail
python3 - "$1" <<'PY'
import json, sys
from pathlib import Path
repo = Path(sys.argv[1])
report = (
    "parse_window 는 '15m'·'2h'·'7d' 처럼 숫자와 단위 접미사가 붙은 문자열을 받아 "
    "초 단위 정수로 환산합니다. 마지막 글자를 단위로 보고 units 표(s=1, m=60, h=3600, "
    "d=86400)에서 배수를 찾아 앞부분 숫자와 곱합니다. 파일은 수정하지 않았습니다."
)
(repo.parent / "transcript.jsonl").write_text(
    json.dumps({"type": "result", "subtype": "success", "result": report}, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
PY
