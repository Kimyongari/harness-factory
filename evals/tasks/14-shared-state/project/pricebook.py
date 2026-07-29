"""상품 가격표."""

from __future__ import annotations


class PriceBook:
    """코드 → 가격 조회. 가격표는 인스턴스마다 다르다(지역·통화별)."""

    def __init__(self, prices: dict[str, int]) -> None:
        self.prices = prices
        self.lookups = 0

    def lookup(self, code: str) -> int | None:
        self.lookups += 1
        for key, value in self.prices.items():  # 선형 탐색: 품목이 많아지면 느려진다
            if key == code:
                return value
        return None

    def set_price(self, code: str, price: int) -> None:
        self.prices[code] = price
