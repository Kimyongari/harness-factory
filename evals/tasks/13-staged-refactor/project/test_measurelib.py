"""measurelib 현재 동작 테스트 — 리팩터링 전 기준선. 전부 통과 상태를 유지해야 한다."""

import measurelib
import pytest


def test_parse_full_line():
    assert measurelib.parse_reading("TEMP-A1 23.5C @2024-03-01T10:00 [cal]") == {
        "sensor": "TEMP-A1",
        "value": 23.5,
        "unit": "C",
        "timestamp": "2024-03-01T10:00",
        "flags": ["cal"],
    }


def test_parse_optional_parts_absent():
    assert measurelib.parse_reading("PRES-02 101.3kPa") == {
        "sensor": "PRES-02",
        "value": 101.3,
        "unit": "kPa",
        "timestamp": None,
        "flags": [],
    }


def test_parse_unit_alias_and_flag_spacing():
    reading = measurelib.parse_reading("HUM-3 40degc [cal, ok]")
    assert reading["unit"] == "C"
    assert reading["value"] == 40.0
    assert reading["flags"] == ["cal", "ok"]


def test_parse_rejects_unknown_unit():
    with pytest.raises(ValueError):
        measurelib.parse_reading("TEMP-A1 23.5parsec")


def test_parse_rejects_bad_sensor_id():
    with pytest.raises(ValueError):
        measurelib.parse_reading("temp_a1 23.5C")


def test_parse_batch_skips_blank_and_comments():
    text = "# 헤더\nTEMP-A1 68F\n\nCLK-9 3s"
    assert [r["sensor"] for r in measurelib.parse_batch(text)] == ["TEMP-A1", "CLK-9"]


def test_parse_batch_error_carries_line_number():
    with pytest.raises(ValueError, match="line 3"):
        measurelib.parse_batch(["TEMP-A1 20C", "# 주석", "TEMP-A1 20wat"])


def test_convert_temperature():
    assert measurelib.convert(212, "F", "C") == 100.0
    assert measurelib.convert(0, "C", "K") == 273.15


def test_convert_linear_units():
    assert measurelib.convert(1, "bar", "kPa") == 100.0
    assert measurelib.convert(90000, "ms", "min") == 1.5


def test_convert_cross_category_raises():
    with pytest.raises(ValueError):
        measurelib.convert(1, "C", "kPa")


def test_format_plain_and_compact():
    reading = measurelib.parse_reading("TEMP-A1 23.5C @2024-03-01T10:00 [cal]")
    assert measurelib.format_reading(reading) == "TEMP-A1: 23.5 °C [cal]"
    assert measurelib.format_reading(reading, "compact") == "TEMP-A1=23.5C"


def test_format_csv_with_and_without_optionals():
    with_all = measurelib.parse_reading("TEMP-A1 23.5C @2024-03-01T10:00 [cal]")
    bare = measurelib.parse_reading("PRES-02 101.3kPa")
    assert measurelib.format_reading(with_all, "csv") == "TEMP-A1,23.5,C,2024-03-01T10:00,cal"
    assert measurelib.format_reading(bare, "csv") == "PRES-02,101.3,kPa,,"


def test_format_table_alignment():
    readings = measurelib.parse_batch(
        "TEMP-A1 23.5C @2024-03-01T10:00 [cal]\nPRES-02 101.3kPa\nCLK-9 90000ms @2024-03-02T00:00"
    )
    assert measurelib.format_table(readings) == (
        "SENSOR   VALUE      TIME\n"
        "TEMP-A1  23.5 °C    2024-03-01T10:00\n"
        "PRES-02  101.3 kPa  -\n"
        "CLK-9    90000 ms   2024-03-02T00:00"
    )


def test_process_line_converts_then_formats():
    assert measurelib.process_line("PRES-02 1.5bar @2024-03-01T10:05", target_unit="kPa") == (
        "PRES-02: 150 kPa"
    )


def test_process_batch_end_to_end():
    assert measurelib.process_batch("TEMP-A1 68F", target_unit="C") == ["TEMP-A1: 20 °C"]
