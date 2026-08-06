"""장바구니 합계. 대량 구매 할인 정책:

  - 같은 품목을 10개 이상 담으면 그 품목에 5% 할인
  - 주문 전체 금액이 500.00 이상이면 추가 2% 할인 (품목 할인 적용 후 기준)
"""

from money import apply_discount, to_cents

BULK_QTY = 10
BULK_PCT = 5
ORDER_THRESHOLD_CENTS = 50_000
ORDER_PCT = 2


def line_total(unit_price: float, qty: int) -> int:
    """품목 한 줄의 합계(센트). 대량 구매면 품목 할인을 적용한다."""
    subtotal = to_cents(unit_price) * qty
    if qty >= BULK_QTY:
        return apply_discount(subtotal, BULK_PCT)
    return subtotal


def order_total(lines: list[tuple[float, int]]) -> int:
    """주문 전체 합계(센트). 전체 금액 할인은 품목 할인 뒤에 적용한다."""
    total = sum(line_total(price, qty) for price, qty in lines)
    if total >= ORDER_THRESHOLD_CENTS:
        return apply_discount(total, ORDER_PCT)
    return total
