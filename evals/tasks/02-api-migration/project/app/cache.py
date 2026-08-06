"""캐시 계층 설정."""

from config.legacy import get


def ttl_seconds() -> int:
    return int(get("cache", "ttl_seconds", "300"))


def backend() -> str:
    return get("cache", "backend", "memory")
