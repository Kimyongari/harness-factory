"""채점: 3세션 단계 리팩터링 — 산출물(모듈 구조·행동·계획 문서)의 성질만 본다.

세션이 몇 번에 나눠 끝냈는지는 재지 않는다(러너가 세션을 쪼갠다). 재는 것은
"컨텍스트가 사라져도 완주할 수 있게 상태를 파일에 남겼는가" 의 최종 증거다:
새 모듈 2개 + 재수출 셔틀 + 행동 보존 + REFACTOR_PLAN.md 의 체크·진행 기록.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ORIG_PLAN = Path(__file__).resolve().parents[1] / "project" / "REFACTOR_PLAN.md"

ws = workspace()
r = Report()


def _private_boundary_violations(source: str) -> list[str]:
    """measure_format 이 measure_parser 의 밑줄(_) 이름을 쓰는 자리를 찾는다."""
    hits: list[str] = []
    aliases = {"measure_parser", *re.findall(r"import\s+measure_parser\s+as\s+(\w+)", source)}
    for alias in aliases:
        hits += re.findall(rf"\b{alias}\s*\.\s*_\w+", source)
    for names in re.findall(r"from\s+measure_parser\s+import\s+([^\n]+)", source):
        hits += [n for n in re.split(r"[,\s()]+", names) if n.startswith("_")]
    return hits


# ① 구조: 새 모듈 2개 존재 + 모듈 경계(공개 API만) + 재수출 셔틀 동작.
parser_file = ws / "measure_parser.py"
format_file = ws / "measure_format.py"
violations = (
    _private_boundary_violations(format_file.read_text(encoding="utf-8", errors="ignore"))
    if format_file.exists()
    else []
)
structure_ok, structure_log = (
    run_heldout(ws, HELDOUT, expr="structure")
    if parser_file.exists() and format_file.exists()
    else (False, "measure_parser.py/measure_format.py 없음")
)
passed = parser_file.exists() and format_file.exists() and not violations and structure_ok
detail = f"내부 이름 교차 참조: {violations}" if violations else ("" if passed else structure_log)
r.add("structure", "모듈 분리 구조(2개 모듈+공개 경계+재수출 셔틀)", 0.25, passed, detail)

# ② 행동 보존(gate): 새 모듈이 원래 measurelib 과 동일하게 동작하는가.
#    시작 상태에는 모듈이 없어 반드시 실패한다.
ok, log = run_heldout(ws, HELDOUT, expr="behavior")
r.add(
    "behavior_preserved",
    "새 모듈의 파싱·변환·포맷 행동 보존",
    0.35,
    ok,
    log if not ok else "",
    gate=True,
)

# ③ 기존 테스트 그린: measurelib 경유 레거시 동작(held-out 사본으로 판정 —
#    작업공간의 test_measurelib.py 를 고쳐서 통과시키는 self-fulfilling 을 막는다).
ok, log = run_heldout(ws, HELDOUT, expr="legacy")
r.add("legacy_green", "measurelib 경유 기존 동작 유지", 0.15, ok, log if not ok else "")

# ④ 계획 문서: 세 단계 모두 체크 + 진행 기록이 남아 있는가.
plan_path = ws / "REFACTOR_PLAN.md"
plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
stages_checked = all(re.search(rf"\[[xX]\][^\n]*단계\s*{n}", plan_text) for n in (1, 2, 3))


# 진행 기록: 원본 계획에 없던 비어 있지 않은 줄이 추가됐는가(체크박스 상태는 무시).
def _norm_lines(text: str) -> set[str]:
    return {re.sub(r"\[[xX]\]", "[ ]", line.strip()) for line in text.splitlines() if line.strip()}


orig_lines = _norm_lines(ORIG_PLAN.read_text(encoding="utf-8"))
new_lines = _norm_lines(plan_text) - orig_lines
plan_ok = bool(plan_text) and stages_checked and bool(new_lines)
r.add(
    "plan_updated",
    "REFACTOR_PLAN.md 세 단계 체크 + 진행 기록 존재",
    0.25,
    plan_ok,
    "" if plan_ok else f"checked={stages_checked}, 추가 기록 줄={len(new_lines)}",
)

r.emit()
