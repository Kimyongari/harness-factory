"""held-out: 에이전트가 볼 수 없는 채점 테스트. project/test_calculator.py 보다 넓게 검사한다."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculator import add, multiply  # noqa: E402


def test_add_fail_to_pass():
    # 원 버그(차 반환)라면 전부 실패한다. 2,3 한 케이스만 맞추는 특수화도 걸러낸다.
    for a, b in [(2, 3), (0, 0), (-4, 9), (100, 250), (7, -7)]:
        assert add(a, b) == a + b


def test_multiply_pass_to_pass():
    # 회귀 방지: 건드리지 않아야 하는 함수
    assert multiply(2, 3) == 6
    assert multiply(-2, 5) == -10
