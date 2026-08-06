"""measure_parser — 센서 측정 라인 파싱과 단위 변환 (measurelib 에서 분리).

공개 API: parse_reading · parse_batch · convert · normalize_unit.
normalize_unit 은 포맷 계층이 내부 헬퍼(_normalize_unit)에 의존하던 것을
공개 함수로 승격한 것이다.
"""

from __future__ import annotations

import re

_UNIT_ALIASES = {
    "c": "C",
    "degc": "C",
    "celsius": "C",
    "f": "F",
    "degf": "F",
    "fahrenheit": "F",
    "k": "K",
    "kelvin": "K",
    "pa": "Pa",
    "kpa": "kPa",
    "bar": "bar",
    "ms": "ms",
    "s": "s",
    "sec": "s",
    "min": "min",
}

_SENSOR_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$")
_VALUE_UNIT_RE = re.compile(r"^([-+]?\d+(?:\.\d+)?)([A-Za-z]+)$")
_FLAGS_RE = re.compile(r"\[([^\[\]]*)\]\s*$")


def normalize_unit(unit: str) -> str:
    """단위 표기를 정준 단위로 정규화한다. 모르는 단위는 ValueError.

    >>> normalize_unit("degC")
    'C'
    """
    key = str(unit).strip().lower()
    if key not in _UNIT_ALIASES:
        raise ValueError(f"unknown unit: {unit!r}")
    return _UNIT_ALIASES[key]


def _extract_flags(line: str) -> tuple[str, list[str]]:
    """라인 끝의 [flag,...] 구간을 떼어 (본문, 플래그 목록) 을 돌려준다."""
    match = _FLAGS_RE.search(line)
    if not match:
        return line, []
    flags = [token.strip() for token in match.group(1).split(",")]
    return line[: match.start()].rstrip(), [token for token in flags if token]


def _split_value_unit(token: str) -> tuple[float, str]:
    """'23.5C' 같은 값+단위 토큰을 (float 값, 정준 단위) 로 쪼갠다."""
    match = _VALUE_UNIT_RE.match(token)
    if not match:
        raise ValueError(f"bad value token: {token!r}")
    return float(match.group(1)), normalize_unit(match.group(2))


def parse_reading(line: str) -> dict:
    """측정 라인 하나를 파싱한다.

    반환 dict 의 키(계약): sensor(str) · value(float) · unit(정준 단위 str) ·
    timestamp(str | None) · flags(list[str], 없으면 빈 목록).
    형식 위반은 전부 ValueError.
    """
    if not isinstance(line, str) or not line.strip():
        raise ValueError("empty measurement line")
    body, flags = _extract_flags(line.strip())
    tokens = body.split()
    if len(tokens) < 2:
        raise ValueError(f"malformed line: {line!r}")
    sensor = tokens[0]
    if not _SENSOR_RE.match(sensor):
        raise ValueError(f"bad sensor id: {sensor!r}")
    value, unit = _split_value_unit(tokens[1])
    timestamp: str | None = None
    for extra in tokens[2:]:
        if extra.startswith("@"):
            if timestamp is not None:
                raise ValueError(f"duplicate timestamp in: {line!r}")
            timestamp = extra[1:]
            if not timestamp:
                raise ValueError(f"empty timestamp in: {line!r}")
        else:
            raise ValueError(f"unexpected token: {extra!r}")
    return {
        "sensor": sensor,
        "value": value,
        "unit": unit,
        "timestamp": timestamp,
        "flags": flags,
    }


def parse_batch(lines) -> list[dict]:
    """여러 라인을 파싱한다. 빈 라인·'#' 주석은 건너뛰고, 실패는
    "line <원본 라인 번호>: <원인>" ValueError 로 바꿔 던진다."""
    if isinstance(lines, str):
        lines = lines.splitlines()
    readings: list[dict] = []
    for lineno, raw in enumerate(lines, start=1):
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        try:
            readings.append(parse_reading(text))
        except ValueError as exc:
            raise ValueError(f"line {lineno}: {exc}") from None
    return readings


# ------------------------------------------------------------------- 단위 변환
_LINEAR_TO_BASE = {
    "Pa": 1.0,
    "kPa": 1000.0,
    "bar": 100000.0,
    "ms": 1.0,
    "s": 1000.0,
    "min": 60000.0,
}

_CATEGORY = {
    "C": "temperature",
    "F": "temperature",
    "K": "temperature",
    "Pa": "pressure",
    "kPa": "pressure",
    "bar": "pressure",
    "ms": "duration",
    "s": "duration",
    "min": "duration",
}


def _to_kelvin(value: float, unit: str) -> float:
    if unit == "K":
        return value
    if unit == "C":
        return value + 273.15
    return (value - 32.0) * 5.0 / 9.0 + 273.15  # F


def _from_kelvin(value: float, unit: str) -> float:
    if unit == "K":
        return value
    if unit == "C":
        return value - 273.15
    return (value - 273.15) * 9.0 / 5.0 + 32.0  # F


def convert(value: float, unit: str, target_unit: str) -> float:
    """value 를 unit 에서 target_unit 으로 변환한다. 카테고리가 다르면 ValueError.
    결과는 소수 6자리로 반올림한다.

    >>> convert(212, "F", "C")
    100.0
    """
    src = normalize_unit(unit)
    dst = normalize_unit(target_unit)
    if _CATEGORY[src] != _CATEGORY[dst]:
        raise ValueError(f"cannot convert {src} -> {dst}")
    if src == dst:
        return float(value)
    if _CATEGORY[src] == "temperature":
        out = _from_kelvin(_to_kelvin(float(value), src), dst)
    else:
        out = float(value) * _LINEAR_TO_BASE[src] / _LINEAR_TO_BASE[dst]
    return round(out, 6)
