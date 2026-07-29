"""상품 가격표."""

from __future__ import annotations


class PriceBook:
    """코드 → 가격 조회. 가격표는 인스턴스마다 다르다(지역·통화별)."""

    def __init__(self, prices: dict[str, int]) -> None:
        self.prices = prices
        self.lookups = 0
        self._cache: dict[str, int | None] = {}  # 인스턴스별 캐시 — 공유하지 않는다

    def lookup(self, code: str) -> int | None:
        if code in self._cache:
            return self._cache[code]
        self.lookups += 1
        result = None
        for key, value in self.prices.items():
            if key == code:
                result = value
                break
        self._cache[code] = result
        return result

    def set_price(self, code: str, price: int) -> None:
        self.prices[code] = price
        self._cache.pop(code, None)  # 값이 바뀌면 캐시를 무효화한다
