"""held-out: 할인 계산과 회귀. project 의 테스트보다 넓게 본다."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from invoice import calc_total  # noqa: E402

ITEMS = [{"price": 100.0, "qty": 2}, {"price": 50.0, "qty": 1}]


def test_discount_applied():
    assert calc_total(ITEMS, 0.1) == 225.0
    assert calc_total(ITEMS, 0.5) == 125.0
    assert calc_total(ITEMS, 1.0) == 0.0


def test_pass_to_pass():
    assert calc_total(ITEMS) == 250.0
    assert calc_total(ITEMS, 0.0) == 250.0
    assert calc_total([]) == 0.0
