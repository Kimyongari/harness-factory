import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greeter import greet  # noqa: E402


def test_greeting_changed():
    out = greet("철수")
    assert "안녕하세요" in out and "철수" in out and "님" in out


def test_no_english_greeting():
    assert "Hello" not in greet("철수")
