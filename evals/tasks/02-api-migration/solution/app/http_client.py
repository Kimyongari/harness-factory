"""외부 API 호출 클라이언트 설정."""

from config.store import lookup

DEFAULT_RETRIES = 3


def retry_limit() -> int:
    """재시도 횟수. 설정에 값이 명시돼 있으면 그 값을, 없으면 DEFAULT_RETRIES.

    구 API 에서는 "값이 있으면 비어 있지 않은 str" 이라 truthiness 로 존재를
    판별했다. 신 API 는 0 같은 falsy 값을 그대로 돌려주므로 None 비교로 바꾼다.
    """
    raw = lookup("http.retries")
    if raw is not None:
        return int(raw)
    return DEFAULT_RETRIES


def timeout_seconds() -> float:
    return float(lookup("http.timeout", default=5.0))


def user_agent() -> str:
    return lookup("http.user_agent", default="app/1.0")
