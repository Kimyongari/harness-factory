"""항목 변환 파이프라인."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def transform(item: dict) -> dict:
    """항목을 정규화한다. 필수 키가 없으면 KeyError."""
    return {"id": item["id"], "name": item["name"].strip().lower()}


def process(items: list[dict]) -> list[dict]:
    """모든 항목을 변환해 목록으로 돌려준다. 실패한 항목은 건너뛰고 기록한다.

    실패 내역은 반환 목록의 `failures` 속성과 로그 양쪽으로 관찰할 수 있다.
    KeyboardInterrupt·SystemExit 은 잡지 않는다 — 중단 가능성을 유지한다.
    """
    results: list[dict] = []
    failures: list[tuple[object, str]] = []
    for index, item in enumerate(items):
        try:
            results.append(transform(item))
        except Exception as exc:  # BaseException 은 잡지 않는다
            key = item.get("id", index) if isinstance(item, dict) else index
            failures.append((key, f"{type(exc).__name__}: {exc}"))
            logger.warning("항목 처리 실패 item=%r error=%s: %s", key, type(exc).__name__, exc)
    if failures:
        logger.warning("실패 %d건: %s", len(failures), failures)
    return results
