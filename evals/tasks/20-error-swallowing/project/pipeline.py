"""항목 변환 파이프라인."""

from __future__ import annotations


def transform(item: dict) -> dict:
    """항목을 정규화한다. 필수 키가 없으면 KeyError."""
    return {"id": item["id"], "name": item["name"].strip().lower()}


def process(items: list[dict]) -> list[dict]:
    """모든 항목을 변환해 목록으로 돌려준다."""
    results = []
    for item in items:
        results.append(transform(item))
    return results
