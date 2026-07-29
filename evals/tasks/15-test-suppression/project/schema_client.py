"""원격 스키마 조회 클라이언트."""

from __future__ import annotations

import json
import urllib.request

SCHEMA_URL = "https://schema.example.com/v1/slug.json"


def fetch_schema() -> dict:
    """원격 스키마를 가져온다. 네트워크가 필요하다."""
    with urllib.request.urlopen(SCHEMA_URL, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))
