"""시간 윈도 문자열 파서."""


def parse_window(spec: str) -> int:
    """'15m' · '2h' · '7d' 같은 문자열을 초 단위 정수로 바꾼다."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    value, suffix = spec[:-1], spec[-1]
    return int(value) * units[suffix]


def humanize(seconds: int) -> str:
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size:
            return f"{seconds // size}{unit}"
    return f"{seconds}s"
