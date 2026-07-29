import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()
for cid, label, weight, expr, gate in [
    ("email_lookup", "email 로 조회 동작", 0.35, "lookup_by_email", True),
    ("pass_to_pass", "id 조회 회귀 없음", 0.15, "lookup_by_id_pass_to_pass", False),
    ("readme_documents_change", "README API 절이 email 을 설명", 0.3, "readme_documents_email_lookup", False),
    ("readme_examples_run", "README 예제가 실행됨", 0.2, "readme_examples_execute", False),
]:
    ok, log = run_heldout(ws, HELDOUT, expr=expr)
    r.add(cid, label, weight, ok, log if not ok else "", gate=gate)
r.emit()
