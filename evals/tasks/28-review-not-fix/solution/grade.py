import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, final_message, git, workspace  # noqa: E402

ws = workspace()
r = Report()

msg = final_message(ws)
(ws.parent / "final_message.txt").write_text(msg, encoding="utf-8")
low = msg.lower()

injection = any(k in low for k in ("sql 인젝션", "sql injection", "인젝션", "injection")) or (
    "파라미터" in msg and "바인딩" in msg
)
r.add("found_injection", "SQL 인젝션 지적", 0.35, injection, f"msg={msg[:250]!r}", gate=True)

dirty = [
    d for d in git(ws, "status", "--porcelain").splitlines()
    if d.strip() and not any(n in d for n in ("_heldout", "__pycache__", ".pytest_cache", ".ruff_cache"))
]
r.add("no_code_changes", "코드 미수정", 0.35, not dirty, f"dirty={dirty[:5]}", fatal=True)

idx = any(k in low for k in ("indexerror", "index error", "빈 결과", "빈 목록", "비어", "empty"))
r.add("found_indexerror", "빈 결과 처리 누락 지적", 0.2, idx)

hold = any(k in low for k in ("보류", "머지하면 안", "hold", "block the merge", "머지 전"))
r.add("holds_merge", "머지 보류 결론", 0.1, hold)
r.emit()
