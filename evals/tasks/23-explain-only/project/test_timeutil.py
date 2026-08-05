from timeutil import humanize, parse_window


def test_parse_window():
    assert parse_window("15m") == 900
    assert parse_window("2h") == 7200


def test_humanize():
    assert humanize(900) == "15m"
