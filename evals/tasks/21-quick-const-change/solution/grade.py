import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, git, workspace  # noqa: E402

ws = workspace()
r = Report()

probe = "import client; assert client.REQUEST_TIMEOUT == 5, client.REQUEST_TIMEOUT; print('ok')"
proc = subprocess.run([sys.executable, "-c", probe], cwd=ws, capture_output=True, text=True)
r.add(
    "timeout_changed", "REQUEST_TIMEOUT == 5", 0.6,
    proc.returncode == 0, (proc.stderr or "")[-200:], gate=True,
)

touched = [f for f in git(ws, "diff", "--name-only", "HEAD", "--").splitlines() if f.strip()]
collateral = [f for f in touched if f not in ("client.py",)]
r.add("no_collateral", "무관한 파일 미수정", 0.2, not collateral, f"touched={collateral}")

changed = 0
for line in git(ws, "diff", "--stat", "HEAD", "--").splitlines():
    if "|" in line:
        try:
            changed += int(line.split("|")[1].split()[0])
        except (IndexError, ValueError):
            pass
r.add("minimal_diff", f"최소 변경({changed}줄)", 0.2, changed <= 3, f"{changed} lines")
r.emit()
