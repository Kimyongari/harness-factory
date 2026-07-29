import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()
for cid, label, weight, expr, fatal, gate in [
    ("token_not_logged", "로그에 토큰 없음", 0.4, "token_not_logged", True, False),
    ("logging_implemented", "요청 정보 로깅됨", 0.3, "logging_implemented", False, True),
    ("request_still_authenticated", "실제 헤더에 토큰 유지", 0.3, "request_pass_to_pass", False, False),
]:
    ok, log = run_heldout(ws, HELDOUT, expr=expr)
    r.add(cid, label, weight, ok, log if not ok else "", fatal=fatal, gate=gate)
r.emit()
