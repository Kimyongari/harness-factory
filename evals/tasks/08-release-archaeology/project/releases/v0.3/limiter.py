"""고정 윈도 요율 제한기."""

import time

import config
from store import MemoryStore


class RateLimiter:
    def __init__(self, limit: int = config.DEFAULT_LIMIT, clock=time.monotonic):
        self.limit = limit
        self._clock = clock
        self._store = MemoryStore()

    def _window_start(self) -> float:
        now = self._clock()
        return now - (now % config.WINDOW_SECONDS)

    def check(self, key: str) -> bool:
        bucket = self._store.bucket_for(key, self._window_start())
        bucket.count += 1
        return bucket.count <= self.limit

    def remaining(self, key: str) -> int:
        bucket = self._store.bucket_for(key, self._window_start())
        return self.limit - bucket.count

    def reset(self, key: str) -> None:
        self._store.drop(key)

    def purge(self) -> int:
        return self._store.purge_expired(self._window_start())
