"""플러그인 매니페스트 로더."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

MANIFEST_DIR = Path(__file__).parent / "manifests"
YAML_SUFFIXES = {".yaml", ".yml"}


def load_manifest(path: str | Path) -> dict:
    """매니페스트 파일을 읽어 dict 로 돌려준다. JSON 과 YAML 을 지원."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in YAML_SUFFIXES:
        # safe_load: 임의 파이썬 객체 태그(!!python/object/...)를 실행하지 않는다.
        return yaml.safe_load(text)
    return json.loads(text)


def list_manifests() -> list[str]:
    return sorted(p.name for p in MANIFEST_DIR.iterdir() if p.is_file())
