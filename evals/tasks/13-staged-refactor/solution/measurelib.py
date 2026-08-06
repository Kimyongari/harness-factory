"""measurelib — 하위호환 재수출 셔틀.

파싱·단위 변환은 measure_parser, 포맷은 measure_format 이 소유한다.
이 모듈은 기존 공개 이름을 재수출하고, 두 모듈을 조합하는 레거시 진입점
(process_line · process_batch)만 남긴다.
"""

from __future__ import annotations

from measure_format import format_reading, format_table
from measure_parser import convert, normalize_unit, parse_batch, parse_reading

__all__ = [
    "convert",
    "format_reading",
    "format_table",
    "normalize_unit",
    "parse_batch",
    "parse_reading",
    "process_batch",
    "process_line",
]


def _converted(reading: dict, target_unit: str | None) -> dict:
    if target_unit is None:
        return reading
    return dict(
        reading,
        value=convert(reading["value"], reading["unit"], target_unit),
        unit=normalize_unit(target_unit),
    )


def process_line(line: str, target_unit: str | None = None, style: str = "plain") -> str:
    """라인 하나를 파싱하고 (선택) 변환한 뒤 포맷한다."""
    return format_reading(_converted(parse_reading(line), target_unit), style=style)


def process_batch(lines, target_unit: str | None = None, style: str = "plain") -> list[str]:
    """여러 라인을 parse_batch 규칙(빈 줄·주석 건너뜀)으로 처리한다."""
    return [
        format_reading(_converted(reading, target_unit), style=style)
        for reading in parse_batch(lines)
    ]
