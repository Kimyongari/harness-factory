from invoice import calc_total


def test_total_without_discount():
    assert calc_total([{"price": 100.0, "qty": 2}]) == 200.0
