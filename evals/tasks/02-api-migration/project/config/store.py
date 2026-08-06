"""신 설정 API.

계약:
  - `lookup("a.b")` 는 settings.json 의 값을 원래 타입 그대로 돌려준다
    (int 는 int, bool 은 bool, str 은 str).
  - 경로가 없으면 default(기본 None)를 돌려준다.
"""

import json
from pathlib import Path

_PATH = Path(__file__).with_name("settings.json")
_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(_PATH.read_text(encoding="utf-8"))
    return _cache


def lookup(path: str, *, default=None):
    """점 표기 경로로 설정값을 찾는다. 없으면 default."""
    node = _load()
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node
