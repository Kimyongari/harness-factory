"""캐시 계층 설정."""

from config.store import lookup


def ttl_seconds() -> int:
    return int(lookup("cache.ttl_seconds", default=300))


def backend() -> str:
    return lookup("cache.backend", default="memory")
