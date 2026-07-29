import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, git, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()

ok, log = run_heldout(ws, HELDOUT, expr="fail_to_pass")
r.add("fail_to_pass", "add 가 합을 반환(5케이스)", 0.6, ok, log if not ok else "", gate=True)

ok, log = run_heldout(ws, HELDOUT, expr="pass_to_pass")
r.add("pass_to_pass", "multiply 회귀 없음", 0.3, ok, log if not ok else "")

diff = git(ws, "diff", "--stat", "HEAD", "--", ".")
changed = 0
for line in diff.splitlines():
    if "|" in line:
        try:
            changed += int(line.split("|")[1].split()[0])
        except (IndexError, ValueError):
            pass
r.add("scope", f"변경 범위 최소({changed}줄)", 0.1, changed <= 12, f"{changed} lines changed")
r.emit()
