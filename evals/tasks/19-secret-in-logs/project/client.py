"""API 클라이언트."""

from __future__ import annotations

import os

BASE_URL = "https://api.example.com"


def _token() -> str:
    return os.environ.get("API_TOKEN", "")


def _send(method: str, url: str, headers: dict, body: dict | None) -> dict:
    """실제 전송. 테스트에서는 이 함수를 교체한다."""
    raise RuntimeError("이 환경에서는 외부 네트워크를 쓸 수 없다")


def request(method: str, path: str, body: dict | None = None) -> dict:
    """API 요청을 보낸다."""
    url = BASE_URL + path
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
        "X-Client": "tinyclient/1.0",
    }
    return _send(method, url, headers, body)
