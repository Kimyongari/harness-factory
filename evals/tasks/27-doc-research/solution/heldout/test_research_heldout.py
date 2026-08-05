"""held-out: 올바른 파라미터로 재시도가 설정됐는가."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client import make_client


def test_uses_max_attempts():
    c = make_client("k")
    assert c.max_attempts > 1, "재시도가 설정되지 않았다"


def test_client_constructible():
    assert make_client("k").api_key == "k"
