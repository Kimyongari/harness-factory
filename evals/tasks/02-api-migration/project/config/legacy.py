"""구 설정 API (deprecated). 새 코드는 config.store.lookup 을 쓴다.

계약:
  - 반환값은 항상 str 이다. bool 은 "true"/"false", 그 외는 str(value).
  - (section, key) 가 설정에 없으면 default("")를 그대로 돌려준다.
"""

from config.store import lookup

_MISSING = object()


def get(section: str, key: str, default: str = "") -> str:
    value = lookup(f"{section}.{key}", default=_MISSING)
    if value is _MISSING:
        return default
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
