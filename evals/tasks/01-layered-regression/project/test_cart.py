"""보이는 테스트 — 정수 금액만 다뤄서 반올림 경계는 건드리지 않는다."""

from cart import line_total, order_total


def test_line_total_no_discount():
    assert line_total(2.00, 3) == 600


def test_bulk_discount():
    # 10개 "이상" 이면 대량 할인이다.
    assert line_total(10.00, 10) == 9500


def test_bulk_discount_above_threshold():
    assert line_total(10.00, 12) == 11400


def test_order_discount():
    # 품목 할인(9500*2=19000... 아님): 300.00×2 (수량 1씩) = 60000 → 2% 할인
    assert order_total([(300.00, 1), (300.00, 1)]) == 58800


def test_small_order_no_discount():
    assert order_total([(1.00, 2)]) == 200
