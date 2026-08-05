import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, final_message, git, workspace  # noqa: E402

ws = workspace()
r = Report()

msg = final_message(ws)
(ws.parent / "final_message.txt").write_text(msg, encoding="utf-8")

r.add("correct_version", "2.31.0 으로 답함", 0.5, "2.31.0" in msg,
      f"msg={msg[:300]!r}", gate=True)

dirty = [
    d for d in git(ws, "status", "--porcelain").splitlines()
    if d.strip() and not any(n in d for n in ("_heldout", "__pycache__", ".pytest_cache", ".ruff_cache"))
]
r.add("no_edits", "파일 미수정", 0.3, not dirty, f"dirty={dirty[:5]}", fatal=True)

mismatch = "2.28.1" in msg or any(k in msg for k in ("불일치", "다르게", "어긋", "mismatch", "differ"))
r.add("notes_mismatch", "두 파일 불일치 언급", 0.2, mismatch)
r.emit()
