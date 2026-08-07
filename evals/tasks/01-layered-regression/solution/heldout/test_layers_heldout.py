"""held-out — 보이는 테스트가 덮지 않는 계약 경계.

계층 구조: gate(보이는 버그) → money 계약 → refunds 계약 → 회귀.
보이는 테스트는 정수 금액만 다뤄서, 임계값 버그만 고치고 멈춘 실행은
아래 계약 항목에서 떨어진다.
"""

from cart import line_total, order_total
from money import apply_discount, to_cents
from refunds import charge_cents, partial_refund_cents, refund_cents


# ---- gate: 보이는 버그(대량 할인 임계값 off-by-one) --------------------------
def test_gate_bulk_at_threshold():
    assert line_total(10.00, 10) == 9500


def test_gate_bulk_above_threshold():
    assert line_total(10.00, 12) == 11400


# ---- money 계약: 부동소수 흡수 + half away from zero -------------------------
def test_money_float_absorption():
    assert to_cents(0.29) == 29
    assert to_cents(0.07) == 7
    assert to_cents(19.99) == 1999


def test_money_half_away_from_zero():
    assert to_cents(1.005) == 101
    assert to_cents(-1.005) == -101
    assert to_cents(2.675) == 268


def test_money_discount_rounding():
    assert apply_discount(1000, 10) == 900
    assert apply_discount(105, 50) == 53
    assert apply_discount(100, 100) == 0


def test_money_discount_in_cart():
    # 0.29 × 10개: 계약대로면 29×10=290 → 5% 할인 275.5 → 276
    assert line_total(0.29, 10) == 276


# ---- refunds 계약: 청구의 정확한 역 ------------------------------------------
def test_refund_exact_inverse():
    for amount in (1.005, 0.29, 19.99, 2.675):
        assert refund_cents(amount) == -charge_cents(amount)
    assert refund_cents(1.005) == -101


def test_refund_partial_rounding():  # 이름에 'money' 를 넣지 않는다 — 채점 -k 필터가 겹친다
    # to_cents(1.05)=105 → 105×50% = 52.5 → 53 → -53
    assert partial_refund_cents(1.05, 50) == -53
    # to_cents(0.29)=29 → 29×10% = 2.9 → 3 → -3
    assert partial_refund_cents(0.29, 10) == -3


# ---- 회귀: 보이는 동작 유지 ---------------------------------------------------
def test_regression_no_discount():
    assert line_total(2.00, 3) == 600


def test_regression_order_discount():
    assert order_total([(300.00, 1), (300.00, 1)]) == 58800


def test_regression_small_order():
    assert order_total([(1.00, 2)]) == 200
