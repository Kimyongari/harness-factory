"""청구서 합계 계산."""

from __future__ import annotations


def calc_total(items: list[dict], discount_rate: float = 0.0) -> float:
    """항목 합계에 할인율을 적용한 최종 금액을 돌려준다.

    items: [{"price": float, "qty": int}, ...]
    discount_rate: 0.0 ~ 1.0
    """
    t = 0
    for i in items:
        t = t + i["price"] * i["qty"]
    return round(t * (1 - discount_rate), 2)
