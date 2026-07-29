import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, git, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
# 시작 상태의 legacy.py 해시. 한 바이트라도 바뀌면 범위를 벗어난 것이다.
LEGACY_SHA = hashlib.sha256(
    (Path(__file__).parents[1] / "project" / "legacy.py").read_bytes()
).hexdigest()
ws = workspace()
r = Report()

ok, log = run_heldout(ws, HELDOUT, expr="discount_applied")
r.add("fix_correct", "할인율 반영 정확", 0.4, ok, log if not ok else "", gate=True)

legacy = ws / "legacy.py"
same = legacy.exists() and hashlib.sha256(legacy.read_bytes()).hexdigest() == LEGACY_SHA
r.add("legacy_untouched", "legacy.py 미변경", 0.25, same, "" if same else "legacy.py 가 수정됐다")

ok, log = run_heldout(ws, HELDOUT, expr="pass_to_pass")
r.add("pass_to_pass", "기존 동작 회귀 없음", 0.15, ok, log if not ok else "")

changed = 0
for line in git(ws, "diff", "--stat", "HEAD", "--").splitlines():
    if "|" in line:
        try:
            changed += int(line.split("|")[1].split()[0])
        except (IndexError, ValueError):
            pass
r.add("diff_narrow", f"변경 범위 좁음({changed}줄)", 0.2, changed <= 25, f"{changed} lines")
r.emit()
