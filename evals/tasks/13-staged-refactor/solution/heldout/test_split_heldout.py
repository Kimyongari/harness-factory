"""held-out 채점 테스트 — 13-staged-refactor.

세 그룹을 -k 로 나눠 돌린다(이름 토큰이 계약이다):
  behavior_*   새 모듈(measure_parser·measure_format)의 행동 보존. 시작 상태에는
               모듈이 없어 반드시 실패한다 → gate.
  structure_*  재수출 셔틀이 계약대로인가(이름 존재 + 함수 객체 동일 + 진입점 동작).
  legacy_*     measurelib 경유 기존 동작(시작 상태에서도 통과해야 하는 기준선).

주의: import 는 전부 함수 안에서 한다 — 모듈이 없는 시작 상태에서 수집(collection)
자체가 죽으면 legacy 그룹까지 같이 실패해 항목 독립성이 깨진다.
"""

import pytest

# --------------------------------------------------------------- behavior (gate)


def test_behavior_parse_full_and_negative():
    from measure_parser import parse_reading

    assert parse_reading("TEMP-A1 23.5C @2024-03-01T10:00 [cal]") == {
        "sensor": "TEMP-A1",
        "value": 23.5,
        "unit": "C",
        "timestamp": "2024-03-01T10:00",
        "flags": ["cal"],
    }
    assert parse_reading("TEMP-B2 -3.75degF") == {
        "sensor": "TEMP-B2",
        "value": -3.75,
        "unit": "F",
        "timestamp": None,
        "flags": [],
    }


def test_behavior_parse_flags_edges():
    from measure_parser import parse_reading

    assert parse_reading("HUM-3 40degc [cal, ok]")["flags"] == ["cal", "ok"]
    assert parse_reading("HUM-3 40C []")["flags"] == []
    assert parse_reading("VOLT-7 +2.5s [a,,b]")["flags"] == ["a", "b"]


def test_behavior_parse_rejects_malformed():
    from measure_parser import parse_reading

    for bad in (
        "",
        "   ",
        "TEMP-A1",
        "temp-a1 20C",
        "TEMP-A1 20parsec",
        "TEMP-A1 10. C",
        "TEMP-A1 20C @",
        "TEMP-A1 20C @t1 @t2",
        "TEMP-A1 20C extra",
    ):
        with pytest.raises(ValueError):
            parse_reading(bad)


def test_behavior_parse_batch_rules():
    from measure_parser import parse_batch

    text = "# 헤더\nTEMP-A1 68F\n\nCLK-9 3s"
    assert [r["sensor"] for r in parse_batch(text)] == ["TEMP-A1", "CLK-9"]
    with pytest.raises(ValueError, match="line 3"):
        parse_batch(["TEMP-A1 20C", "# 주석", "TEMP-A1 20wat"])


def test_behavior_convert_temperature():
    from measure_parser import convert

    assert convert(212, "F", "C") == 100.0
    assert convert(-40, "F", "C") == -40.0
    assert convert(300, "K", "F") == 80.33
    assert convert(25, "C", "C") == 25.0


def test_behavior_convert_linear_and_errors():
    from measure_parser import convert

    assert convert(1, "bar", "kPa") == 100.0
    assert convert(250, "Pa", "bar") == 0.0025
    assert convert(2.5, "min", "s") == 150.0
    assert convert(90000, "ms", "min") == 1.5
    with pytest.raises(ValueError):
        convert(1, "C", "kPa")
    with pytest.raises(ValueError):
        convert(1, "C", "furlong")


def test_behavior_format_styles():
    from measure_format import format_reading

    full = {
        "sensor": "TEMP-A1",
        "value": 23.5,
        "unit": "C",
        "timestamp": "2024-03-01T10:00",
        "flags": ["cal", "ok"],
    }
    bare = {"sensor": "PRES-02", "value": 150.0, "unit": "kpa", "timestamp": None, "flags": []}
    assert format_reading(full) == "TEMP-A1: 23.5 °C [cal,ok]"
    assert format_reading(full, "csv") == "TEMP-A1,23.5,C,2024-03-01T10:00,cal|ok"
    assert format_reading(full, "compact") == "TEMP-A1=23.5C"
    assert format_reading(bare) == "PRES-02: 150 kPa"
    assert format_reading(bare, "csv") == "PRES-02,150,kPa,,"
    with pytest.raises(ValueError):
        format_reading(full, "yaml")


def test_behavior_format_table_exact():
    from measure_format import format_table
    from measure_parser import parse_batch

    readings = parse_batch(
        "TEMP-A1 23.5C @2024-03-01T10:00 [cal]\nPRES-02 101.3kPa\nCLK-9 90000ms @2024-03-02T00:00"
    )
    assert format_table(readings) == (
        "SENSOR   VALUE      TIME\n"
        "TEMP-A1  23.5 °C    2024-03-01T10:00\n"
        "PRES-02  101.3 kPa  -\n"
        "CLK-9    90000 ms   2024-03-02T00:00"
    )


# ------------------------------------------------------------------- structure


def test_structure_reexports_are_same_objects():
    import measure_format
    import measure_parser
    import measurelib

    for name in ("parse_reading", "parse_batch", "convert"):
        assert getattr(measurelib, name) is getattr(measure_parser, name), name
    for name in ("format_reading", "format_table"):
        assert getattr(measurelib, name) is getattr(measure_format, name), name


def test_structure_entrypoints_still_work():
    import measurelib

    assert measurelib.process_line("PRES-02 1.5bar @2024-03-01T10:05", target_unit="kPa") == (
        "PRES-02: 150 kPa"
    )
    assert measurelib.process_batch("TEMP-A1 68F", target_unit="C") == ["TEMP-A1: 20 °C"]
    assert measurelib.process_batch("# x\nCLK-9 3s", style="compact") == ["CLK-9=3s"]


# ---------------------------------------------------------------------- legacy


def test_legacy_parse_via_measurelib():
    import measurelib

    assert measurelib.parse_reading("TEMP-A1 23.5C @2024-03-01T10:00 [cal]") == {
        "sensor": "TEMP-A1",
        "value": 23.5,
        "unit": "C",
        "timestamp": "2024-03-01T10:00",
        "flags": ["cal"],
    }
    with pytest.raises(ValueError):
        measurelib.parse_reading("TEMP-A1 23.5parsec")
    with pytest.raises(ValueError, match="line 3"):
        measurelib.parse_batch(["TEMP-A1 20C", "# 주석", "TEMP-A1 20wat"])


def test_legacy_convert_via_measurelib():
    import measurelib

    assert measurelib.convert(212, "F", "C") == 100.0
    assert measurelib.convert(1, "bar", "kPa") == 100.0
    with pytest.raises(ValueError):
        measurelib.convert(1, "C", "kPa")


def test_legacy_format_via_measurelib():
    import measurelib

    reading = measurelib.parse_reading("TEMP-A1 23.5C @2024-03-01T10:00 [cal]")
    assert measurelib.format_reading(reading) == "TEMP-A1: 23.5 °C [cal]"
    assert measurelib.format_reading(reading, "csv") == "TEMP-A1,23.5,C,2024-03-01T10:00,cal"


def test_legacy_process_via_measurelib():
    import measurelib

    assert measurelib.process_line("PRES-02 1.5bar @2024-03-01T10:05", target_unit="kPa") == (
        "PRES-02: 150 kPa"
    )
    assert measurelib.process_batch("TEMP-A1 68F", target_unit="C") == ["TEMP-A1: 20 °C"]
