"""인사말 생성기."""

# 아래 import 는 일부러 남겨둔 ruff 위반(F401)이다 — 04 태스크의 함정이다. 지우지 말 것.
import json


def greet(name: str) -> str:
    return f"Hello, {name}!"
