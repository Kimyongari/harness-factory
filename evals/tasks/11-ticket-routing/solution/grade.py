"""채점: held-out 40케이스를 그룹별로 실행한다. 기대값은 cases.json(골든 산출) 고정."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()

# 게이트: 보이는 테스트와 같은 난이도(단일 규칙). 이걸 못 하면 작업 자체를 안 한 것이다.
ok, log = run_heldout(ws, HELDOUT, expr="gate_single_rule")
r.add(
    "gate_basic", "단일 규칙 라우팅(보이는 테스트 수준)", 0.15, ok, log if not ok else "", gate=True
)

# 그룹 ①: urgent × VIP × billing 3중 교차 — 예외의 예외의 예외.
ok, log = run_heldout(ws, HELDOUT, expr="precedence_intersections")
r.add("precedence", "우선순위 교차(urgent×VIP×billing)", 0.25, ok, log if not ok else "")

# 그룹 ②: 영업시간 경계 — UTC→KST 변환·18:00 정각·자정·주말.
ok, log = run_heldout(ws, HELDOUT, expr="time_kst_boundaries")
r.add("time_kst", "영업시간 KST 경계(변환·정각·자정)", 0.25, ok, log if not ok else "")

# 그룹 ③: 언어 변형·첨부 크기 경계·누락 필드.
ok, log = run_heldout(ws, HELDOUT, expr="misc_language_attachments")
r.add("misc_edges", "언어 변형·첨부 경계·누락 필드", 0.20, ok, log if not ok else "")

# 형식·시그니처: route 가 dict 하나를 받아 str 을 돌려주고 입력을 변형하지 않는다.
_SIG_CHECK = """
import copy
from src.router import route
ticket = {
    "id": "SIG-1", "subject_category": "technical", "priority": "normal",
    "vip": False, "language": "en", "created_utc": "2026-08-05T05:00:00Z",
}
snapshot = copy.deepcopy(ticket)
queue = route(ticket)
assert isinstance(queue, str), f"str 이 아니라 {type(queue).__name__}"
assert ticket == snapshot, "route 가 입력 dict 를 변형함"
"""
proc = subprocess.run(
    [sys.executable, "-c", _SIG_CHECK], cwd=ws, capture_output=True, text=True, timeout=60
)
r.add(
    "signature",
    "시그니처(dict→str)·입력 불변",
    0.15,
    proc.returncode == 0,
    (proc.stderr or proc.stdout)[-400:] if proc.returncode != 0 else "",
)

r.emit()
