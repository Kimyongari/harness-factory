"""아주 작은 구조화 로거 — 표준 출력으로 한 줄씩 찍는다."""

from __future__ import annotations


def log_event(name: str, **fields: object) -> None:
    parts = " ".join(f"{key}={value!r}" for key, value in fields.items())
    print(f"[{name}] {parts}")
