"""dedupe 용 TTL 캐시. 시계를 주입할 수 있어 테스트에서 시간을 돌릴 수 있다."""

import time

from . import config


class TTLCache:
    def __init__(self, ttl: int = config.CACHE_TTL, clock=time.monotonic):
        self._ttl_seconds = ttl * 60
        self._clock = clock
        self._store: dict[str, tuple[float, object]] = {}

    def set(self, key: str, value: object) -> None:
        self._store[key] = (self._clock() + self._ttl_seconds, value)

    def get(self, key: str, default=None):
        entry = self._store.get(key)
        if entry is None:
            return default
        expires_at, value = entry
        if self._clock() >= expires_at:
            del self._store[key]
            return default
        return value

    def purge(self) -> int:
        now = self._clock()
        dead = [key for key, (expires_at, _) in self._store.items() if now >= expires_at]
        for key in dead:
            del self._store[key]
        return len(dead)

    def __len__(self) -> int:
        return len(self._store)
