"""외부 API 호출 클라이언트 설정."""

from config.legacy import get

DEFAULT_RETRIES = 3


def retry_limit() -> int:
    """재시도 횟수. 설정에 값이 명시돼 있으면 그 값을, 없으면 DEFAULT_RETRIES."""
    raw = get("http", "retries")
    if raw:
        return int(raw)
    return DEFAULT_RETRIES


def timeout_seconds() -> float:
    return float(get("http", "timeout", "5.0"))


def user_agent() -> str:
    return get("http", "user_agent", "app/1.0")
