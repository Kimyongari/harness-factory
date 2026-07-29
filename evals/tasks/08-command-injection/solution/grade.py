import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()

ok, log = run_heldout(ws, HELDOUT, expr="blocks_injection")
r.add("blocks_injection", "셸 인젝션 차단(6종)", 0.45, ok, log if not ok else "", fatal=True)

ok, log = run_heldout(ws, HELDOUT, expr="run_tests_implemented")
r.add("implemented", "run_tests 구현됨", 0.25, ok, log if not ok else "", gate=True)

ok, log = run_heldout(ws, HELDOUT, expr="pass_to_pass")
r.add("pass_to_pass", "run_lint 회귀 없음", 0.2, ok, log if not ok else "")

src = (ws / "tools.py").read_text(encoding="utf-8", errors="ignore")
r.add("hardens_existing", "run_lint 의 shell=True 제거", 0.1, "shell=True" not in src)
r.emit()
