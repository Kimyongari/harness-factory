import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, git, workspace  # noqa: E402

ws = workspace()
r = Report()
text = (ws / "README.md").read_text(encoding="utf-8", errors="ignore")

fixed = "## Installation" in text and "Instalation" not in text
r.add("typo_fixed", "Instalation → Installation", 0.6, fixed, gate=True)

preserved = "## Usage" in text and "from client import fetch" in text
r.add("content_preserved", "나머지 본문 보존", 0.2, preserved)

changed = 0
for line in git(ws, "diff", "--stat", "HEAD", "--").splitlines():
    if "|" in line:
        try:
            changed += int(line.split("|")[1].split()[0])
        except (IndexError, ValueError):
            pass
r.add("minimal_diff", f"최소 변경({changed}줄)", 0.2, changed <= 3, f"{changed} lines")
r.emit()
