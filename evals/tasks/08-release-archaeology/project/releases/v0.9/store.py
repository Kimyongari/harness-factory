"""키별 윈도 카운터 저장소(메모리)."""


class Bucket:
    __slots__ = ("window_start", "count")

    def __init__(self, window_start: float):
        self.window_start = window_start
        self.count = 0


class MemoryStore:
    def __init__(self):
        self._buckets = {}

    def bucket_for(self, key: str, window_start: float) -> Bucket:
        bucket = self._buckets.get(key)
        if bucket is None or bucket.window_start != window_start:
            bucket = Bucket(window_start)
            self._buckets[key] = bucket
        return bucket

    def drop(self, key: str) -> None:
        self._buckets.pop(key, None)

    def purge_expired(self, current_window_start: float) -> int:
        dead = [k for k, b in self._buckets.items() if b.window_start != current_window_start]
        for k in dead:
            del self._buckets[k]
        return len(dead)

    def stats(self) -> dict:
        return {
            "keys": len(self._buckets),
            "total": sum(b.count for b in self._buckets.values()),
        }
