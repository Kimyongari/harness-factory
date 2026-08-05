import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()

ok, log = run_heldout(ws, HELDOUT, expr="empty_string_handled")
r.add("all_four_fixed", "4개 함수 빈 문자열 처리", 0.5, ok, log if not ok else "", gate=True)

ok_reg, log_reg = run_heldout(ws, HELDOUT, expr="valid_still_pass")
r.add("no_regression", "정상 입력 회귀 없음", 0.2, ok_reg, log_reg if not ok_reg else "")

# 진행 상태를 파일로 남겼는가 — 세션이 끊겨도 살아남는 유일한 기억이다.
notes = []
plan = ws / "PLAN.md"
if plan.exists():
    body = plan.read_text(encoding="utf-8", errors="ignore")
    # 템플릿 그대로(= "(없음)")면 기록한 것이 아니다.
    if "(없음)" not in body and any(k in body for k in ("email", "phone", "postal", "url")):
        notes.append("PLAN.md")
for extra in ws.glob("*.md"):
    if extra.name != "PLAN.md":
        t = extra.read_text(encoding="utf-8", errors="ignore")
        if any(k in t for k in ("email", "phone", "postal", "url")):
            notes.append(extra.name)
r.add("progress_recorded", "진행 상태 기록됨", 0.2, bool(notes), f"notes={notes}")

r.add("continuity", "끊긴 뒤 이어서 완료", 0.1, ok and bool(notes), f"fixed={ok} notes={bool(notes)}")
r.emit()
