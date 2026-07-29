"""플러그인 매니페스트 로더."""

from __future__ import annotations

import json
from pathlib import Path

MANIFEST_DIR = Path(__file__).parent / "manifests"


def load_manifest(path: str | Path) -> dict:
    """매니페스트 파일을 읽어 dict 로 돌려준다. 현재 JSON 만 지원."""
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text)


def list_manifests() -> list[str]:
    return sorted(p.name for p in MANIFEST_DIR.iterdir() if p.is_file())
