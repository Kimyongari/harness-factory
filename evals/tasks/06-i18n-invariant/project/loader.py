"""로케일 메시지 로더."""

from __future__ import annotations

import json
from pathlib import Path

LOCALES = Path(__file__).parent / "locales"
SUPPORTED = ("ko", "en")


def load(lang: str) -> dict[str, str]:
    if lang not in SUPPORTED:
        raise ValueError(f"지원하지 않는 로케일: {lang}")
    return json.loads((LOCALES / f"messages.{lang}.json").read_text(encoding="utf-8"))


def assert_in_sync() -> None:
    """모든 로케일 파일의 키 집합이 동일한지 확인한다. CONTRIBUTING.md 의 불변식."""
    key_sets = {lang: set(load(lang)) for lang in SUPPORTED}
    base = key_sets["ko"]
    for lang, keys in key_sets.items():
        if keys != base:
            missing, extra = base - keys, keys - base
            raise AssertionError(f"{lang} 로케일 키 불일치 — 누락:{sorted(missing)} 초과:{sorted(extra)}")


def t(key: str, lang: str = "ko") -> str:
    return load(lang)[key]
