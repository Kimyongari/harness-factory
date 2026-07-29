from src.parser import parse


def test_parse():
    assert parse("a,b\nc,d") == [["a", "b"], ["c", "d"]]
