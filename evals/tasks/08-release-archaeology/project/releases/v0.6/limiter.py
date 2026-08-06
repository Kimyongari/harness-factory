"""고정 윈도 방식 요율 제한기.

키별로 현재 윈도의 요청 수를 세고, 한도를 넘으면 거부한다.
"""

import time

import config
from store import MemoryStore


def _normalize(key: str) -> str:
    return key.strip().lower()


class RateLimiter:
    def __init__(self, limit: int = config.DEFAULT_LIMIT, clock=time.monotonic):
        self.limit = limit
        self._clock = clock
        self._store = MemoryStore()

    def _window_start(self) -> float:
        now = self._clock()
        return now - (now % config.WINDOW_SECONDS)

    def check(self, key: str) -> dict:
        """현재 윈도에 요청 하나를 집계하고 판정과 잔여량을 돌려준다."""
        key = _normalize(key)
        window_bucket = self._store.bucket_for(key, self._window_start())
        window_bucket.count += 1
        allowed = window_bucket.count <= self.limit
        return {"allowed": allowed, "remaining": self.remaining(key)}

    def remaining(self, key: str) -> int:
        """현재 윈도의 잔여 허용량을 돌려준다."""
        key = _normalize(key)
        window_bucket = self._store.bucket_for(key, self._window_start())
        return self.limit - window_bucket.count

    def reset(self, key: str) -> None:
        """키의 현재 윈도 카운터를 버린다."""
        key = _normalize(key)
        self._store.drop(key)

    def purge(self) -> int:
        """지난 윈도의 버킷을 정리하고 정리된 수를 돌려준다."""
        return self._store.purge_expired(self._window_start())
