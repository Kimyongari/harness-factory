import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()

ok, log = run_heldout(ws, HELDOUT, expr="blocks_traversal")
r.add("blocks_traversal", "경로 탈출 차단(7종)", 0.45, ok, log if not ok else "", fatal=True)

ok, log = run_heldout(ws, HELDOUT, expr="reads_valid_note")
r.add("reads_valid", "정상 노트 읽기 동작", 0.3, ok, log if not ok else "", gate=True)

ok, log = run_heldout(ws, HELDOUT, expr="save_note_still_works")
r.add("pass_to_pass", "save_note/list_notes 회귀 없음", 0.15, ok, log if not ok else "")

src = (ws / "notes.py").read_text(encoding="utf-8", errors="ignore")
save_body = "".join(re.split(r"\ndef ", src)[1:2])
shared = bool(re.search(r"def save_note.*?\n(.*?)(\ndef |\Z)", src, re.S)) and (
    "_note_path" in src or "resolve()" in src or "ValueError" in src
)
r.add("hardens_save", "save_note 에도 검증 적용", 0.1, shared, "" if shared else save_body[:200])
r.emit()
