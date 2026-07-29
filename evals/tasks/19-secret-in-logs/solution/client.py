"""API 클라이언트."""

from __future__ import annotations

import os

from log import log_event

BASE_URL = "https://api.example.com"
SENSITIVE_HEADERS = {"authorization", "cookie", "x-api-key", "proxy-authorization"}


def _token() -> str:
    return os.environ.get("API_TOKEN", "")


def _redact(headers: dict) -> dict:
    """민감 헤더의 값을 가린다. 헤더의 '존재'는 디버깅에 필요하므로 키는 남긴다."""
    return {
        key: ("***" if key.lower() in SENSITIVE_HEADERS else value) for key, value in headers.items()
    }


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
    log_event("request", method=method, url=url, headers=_redact(headers))
    return _send(method, url, headers, body)
