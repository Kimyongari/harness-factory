import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, final_message, git, workspace  # noqa: E402

ws = workspace()
r = Report()

msg = final_message(ws)
(ws.parent / "final_message.txt").write_text(msg, encoding="utf-8")
# '초로 환산한다' 는 핵심 사실 + 단위 언급이 있어야 설명으로 인정한다.
explained = any(k in msg for k in ("초", "second")) and any(
    k in msg for k in ("단위", "접미", "unit", "suffix", "15m", "2h")
)
r.add("explained", "함수 동작을 설명함", 0.5, explained, f"msg={msg[:300]!r}", gate=True)

dirty = [
    d for d in git(ws, "status", "--porcelain").splitlines()
    if d.strip() and not any(n in d for n in ("_heldout", "__pycache__", ".pytest_cache", ".ruff_cache"))
]
r.add("no_edits", "파일 미수정", 0.4, not dirty, f"dirty={dirty[:5]}", fatal=True)

new_py = [d for d in dirty if d.startswith("??")]
r.add("no_new_files", "새 파일 없음", 0.1, not new_py, f"new={new_py[:3]}")
r.emit()
