import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()
for cid, label, weight, expr, fatal, gate in [
    ("blocks_code_execution", "악성 YAML 태그 실행 차단", 0.45, "blocks_code_execution", True, False),
    ("loads_valid_yaml", "정상 YAML 로딩", 0.35, "loads_valid_yaml", False, True),
    ("pass_to_pass", "JSON 로딩 회귀 없음", 0.2, "json_pass_to_pass", False, False),
]:
    ok, log = run_heldout(ws, HELDOUT, expr=expr)
    r.add(cid, label, weight, ok, log if not ok else "", fatal=fatal, gate=gate)
r.emit()
