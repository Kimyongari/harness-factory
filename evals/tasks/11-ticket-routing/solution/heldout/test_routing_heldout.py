"""held-out — 보이는 테스트가 덮지 않는 규칙 교차점.

그룹: gate(단일 규칙) → precedence(urgent×VIP×billing 3중) → time(KST 경계)
→ misc(언어 변형·첨부 경계·누락 필드). 기대값은 cases.json 에 하드코딩돼 있다.
"""

import copy
import json
from pathlib import Path

from src.router import route

CASES = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))


def _run_group(group: str) -> None:
    failures = []
    for case in CASES:
        if case["group"] != group:
            continue
        got = route(copy.deepcopy(case["ticket"]))
        if got != case["expected"]:
            failures.append(f"{case['id']}: got={got!r} expected={case['expected']!r}")
    assert not failures, "; ".join(failures)


def test_gate_single_rule():
    _run_group("gate")


def test_precedence_intersections():
    _run_group("precedence")


def test_time_kst_boundaries():
    _run_group("time")


def test_misc_language_attachments():
    _run_group("misc")
