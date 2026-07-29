from greeter import greet


def test_greet_contains_name():
    assert "철수" in greet("철수")
