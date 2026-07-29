"""held-out: 캐시가 상태를 오염시키지 않는지 본다. 구현 방식에는 중립적이다."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pricebook import PriceBook  # noqa: E402


def test_no_cross_instance_leak():
    """서로 다른 가격표를 쓰는 인스턴스가 상대의 값을 돌려주면 안 된다."""
    seoul = PriceBook({"A": 100})
    tokyo = PriceBook({"A": 900})
    assert seoul.lookup("A") == 100
    assert tokyo.lookup("A") == 900, "다른 인스턴스의 캐시 값이 반환됐다(공유 상태)"
    assert seoul.lookup("A") == 100, "역방향 오염"


def test_cache_invalidated_on_write():
    book = PriceBook({"A": 100})
    assert book.lookup("A") == 100
    book.set_price("A", 150)
    assert book.lookup("A") == 150, "가격 변경 후에도 낡은 캐시가 반환됐다"


def test_cache_actually_caches():
    """같은 코드를 반복 조회하면 실제 탐색은 한 번만 일어나야 한다."""
    book = PriceBook({"A": 100, "B": 200})
    for _ in range(5):
        book.lookup("A")
    assert book.lookups == 1, f"캐시가 동작하지 않는다(탐색 {book.lookups}회)"


def test_pass_to_pass():
    book = PriceBook({"A": 100, "B": 200})
    assert book.lookup("A") == 100
    assert book.lookup("Z") is None
    assert book.lookup("Z") is None  # 미존재 값도 안정적으로 None
