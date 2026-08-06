"""환불 처리.

계약: 환불은 청구의 정확한 역이다 — 어떤 금액이든 refund_cents(x) == -charge_cents(x).
부분 환불은 원 청구와 같은 반올림 규칙을 쓴다.
"""

from money import to_cents


def charge_cents(amount: float) -> int:
    return to_cents(amount)


def refund_cents(amount: float) -> int:
    return to_cents(-amount)


def partial_refund_cents(amount: float, pct: int) -> int:
    """청구 금액의 pct% 를 환불한다. 반올림 규칙은 money 계약을 따른다."""
    return int(to_cents(amount) * pct / 100) * -1
