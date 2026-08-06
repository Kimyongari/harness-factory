"""measure_format — 측정 dict 포맷 (measurelib 에서 분리).

공개 API: format_reading · format_table.
파서와의 경계: measure_parser 의 **공개** 이름(normalize_unit)만 사용한다.
단위 표시 기호는 표시 관심사이므로 이 모듈이 소유한다.
"""

from __future__ import annotations

from measure_parser import normalize_unit

# 정준 단위 → 사람이 읽는 표시 기호.
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
    sensor = reading["sensor"]
    unit = normalize_unit(reading["unit"])
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
            f"{_fmt_num(reading['value'])} {_UNIT_SYMBOLS[normalize_unit(reading['unit'])]}",
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
