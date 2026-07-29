import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()
for cid, label, weight, expr, fatal, gate in [
    ("continues_on_error", "실패 후에도 계속 처리", 0.3, "continues_on_error", False, True),
    ("interrupt_not_swallowed", "KeyboardInterrupt 전파", 0.3, "interrupt_not_swallowed", True, False),
    ("failure_observable", "실패가 관찰 가능", 0.25, "failure_is_observable", False, False),
    ("pass_to_pass", "정상 입력 동작 유지", 0.15, "pass_to_pass", False, False),
]:
    ok, log = run_heldout(ws, HELDOUT, expr=expr)
    r.add(cid, label, weight, ok, log if not ok else "", fatal=fatal, gate=gate)
r.emit()
