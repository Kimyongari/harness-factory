"""measurelib — 센서 측정 라인 파싱·단위 변환·포맷 (레거시 단일 모듈).

측정 라인 형식:
    <SENSOR-ID> <VALUE><UNIT> [@<TIMESTAMP>] [<flags>]

    SENSOR-ID   대문자·숫자 그룹을 하이픈으로 연결 (예: TEMP-A1, PRES-02)
    VALUE       부호 있는 십진수. 단위와 붙여 쓴다 (예: 23.5C, -3.75F, 101.3kPa)
    TIMESTAMP   '@' 로 시작하는 비어 있지 않은 문자열 (예: @2024-03-01T10:00). 선택.
    flags       대괄호 안 쉼표 구분 토큰 (예: [cal,ok]). 선택. 라인 끝에만 온다.

예:
    TEMP-A1 23.5C @2024-03-01T10:00 [cal]
    PRES-02 101.3kPa
"""

from __future__ import annotations

import re

# ============================================================================ 파싱
# 단위 별칭(입력 표기) → 정준 단위. 파서는 항상 정준 단위를 내놓는다.
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

# 정준 단위 → 사람이 읽는 표시 기호 (포맷 계층이 쓴다).
_UNIT_SYMBOLS = {
    "C": "°C",
    "F": "°F",
    "K": "K",
    "Pa": "Pa",
    "kPa": "kPa",
    "bar": "bar",
    "ms": "ms",
    "s": "s",
    "min": "min",
}

_SENSOR_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$")
_VALUE_UNIT_RE = re.compile(r"^([-+]?\d+(?:\.\d+)?)([A-Za-z]+)$")
_FLAGS_RE = re.compile(r"\[([^\[\]]*)\]\s*$")


def _normalize_unit(unit: str) -> str:
    """단위 표기를 정준 단위로 정규화한다. 모르는 단위는 ValueError.

    >>> _normalize_unit("degC")
    'C'
    """
    key = str(unit).strip().lower()
    if key not in _UNIT_ALIASES:
        raise ValueError(f"unknown unit: {unit!r}")
    return _UNIT_ALIASES[key]


def _extract_flags(line: str) -> tuple[str, list[str]]:
    """라인 끝의 [flag,...] 구간을 떼어 (본문, 플래그 목록) 을 돌려준다.

    플래그 토큰 앞뒤 공백은 무시하고, 빈 토큰은 버린다. [] 는 빈 목록이다.
    """
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
    return float(match.group(1)), _normalize_unit(match.group(2))


def parse_reading(line: str) -> dict:
    """측정 라인 하나를 파싱한다.

    반환 dict 의 키(계약): sensor(str) · value(float) · unit(정준 단위 str) ·
    timestamp(str | None) · flags(list[str], 없으면 빈 목록).

    형식 위반은 전부 ValueError: 빈 라인, 잘못된 센서 ID, 값/단위 불일치,
    모르는 단위, '@' 뒤가 빈 타임스탬프, 해석할 수 없는 잉여 토큰, 타임스탬프 중복.
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
    """여러 라인을 파싱한다. 문자열이면 splitlines() 로 나눈다.

    빈 라인과 '#' 로 시작하는 주석 라인은 건너뛴다. 파싱 실패는
    "line <원본 라인 번호>: <원인>" 메시지의 ValueError 로 바꿔 던진다.
    """
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


# ======================================================================== 단위 변환
# 온도는 켈빈을 매개로, 나머지는 카테고리별 기저 단위에 대한 선형 배율로 변환한다.
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
    """value 를 unit 에서 target_unit 으로 변환한다.

    계약: 두 단위 모두 별칭을 허용한다. 서로 다른 카테고리(온도↔압력 등)는
    ValueError. 결과는 부동소수 잡음을 없애기 위해 소수 6자리로 반올림한다.

    >>> convert(212, "F", "C")
    100.0
    """
    src = _normalize_unit(unit)
    dst = _normalize_unit(target_unit)
    if _CATEGORY[src] != _CATEGORY[dst]:
        raise ValueError(f"cannot convert {src} -> {dst}")
    if src == dst:
        return float(value)
    if _CATEGORY[src] == "temperature":
        out = _from_kelvin(_to_kelvin(float(value), src), dst)
    else:
        out = float(value) * _LINEAR_TO_BASE[src] / _LINEAR_TO_BASE[dst]
    return round(out, 6)


# ============================================================================ 포맷
def _fmt_num(value: float) -> str:
    """소수 6자리로 찍고 뒤따르는 0 과 소수점을 제거한다. 150.0 → '150'."""
    text = f"{float(value):.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def format_reading(reading: dict, style: str = "plain") -> str:
    """측정 dict 하나를 문자열로 포맷한다.

    style 계약:
      plain   → "<sensor>: <value> <표시기호>"  (플래그가 있으면 " [f1,f2]" 를 덧붙임)
      csv     → "<sensor>,<value>,<정준단위>,<timestamp|빈칸>,<f1|f2>"
      compact → "<sensor>=<value><정준단위>"
    그 외 style 은 ValueError.
    """
    # NOTE: 파싱 계층의 내부 헬퍼(_normalize_unit)와 내부 테이블(_UNIT_SYMBOLS)을
    # 직접 쓴다 — 같은 모듈 안이라 지금은 문제가 없다.
    sensor = reading["sensor"]
    unit = _normalize_unit(reading["unit"])
    value = _fmt_num(reading["value"])
    flags = list(reading.get("flags") or [])
    timestamp = reading.get("timestamp")
    if style == "plain":
        text = f"{sensor}: {value} {_UNIT_SYMBOLS[unit]}"
        if flags:
            text += " [" + ",".join(flags) + "]"
        return text
    if style == "csv":
        return ",".join([sensor, value, unit, timestamp or "", "|".join(flags)])
    if style == "compact":
        return f"{sensor}={value}{unit}"
    raise ValueError(f"unknown style: {style!r}")


def format_table(readings) -> str:
    """측정 목록을 고정폭 표로 포맷한다.

    열: SENSOR · VALUE(값+표시기호) · TIME(타임스탬프, 없으면 '-').
    각 열 너비는 헤더 포함 최장 셀에 맞춰 ljust, 열 사이는 공백 2칸,
    행 끝 공백은 제거한다.
    """
    rows = [
        (
            reading["sensor"],
            f"{_fmt_num(reading['value'])} {_UNIT_SYMBOLS[_normalize_unit(reading['unit'])]}",
            reading.get("timestamp") or "-",
        )
        for reading in readings
    ]
    header = ("SENSOR", "VALUE", "TIME")
    widths = [max(len(row[i]) for row in [header, *rows]) for i in range(3)]
    lines = [
        "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip()
        for row in [header, *rows]
    ]
    return "\n".join(lines)


# ===================================================================== 레거시 진입점
def process_line(line: str, target_unit: str | None = None, style: str = "plain") -> str:
    """라인 하나를 파싱하고 (선택) 변환한 뒤 포맷한다."""
    reading = parse_reading(line)
    if target_unit is not None:
        reading = dict(
            reading,
            value=convert(reading["value"], reading["unit"], target_unit),
            unit=_normalize_unit(target_unit),
        )
    return format_reading(reading, style=style)


def process_batch(lines, target_unit: str | None = None, style: str = "plain") -> list[str]:
    """여러 라인을 parse_batch 규칙(빈 줄·주석 건너뜀)으로 처리한다."""
    results: list[str] = []
    for reading in parse_batch(lines):
        if target_unit is not None:
            reading = dict(
                reading,
                value=convert(reading["value"], reading["unit"], target_unit),
                unit=_normalize_unit(target_unit),
            )
        results.append(format_reading(reading, style=style))
    return results
