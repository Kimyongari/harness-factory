import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, git, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()

ok, log = run_heldout(ws, HELDOUT, expr="uses_max_attempts")
r.add("retry_configured", "재시도 설정됨", 0.5, ok, log if not ok else "", gate=True)

src = (ws / "client.py").read_text(encoding="utf-8", errors="ignore")
invented = [p for p in ("retry_count", "retries=") if p in src]
r.add(
    "no_invented_param", "없는 파라미터 미사용", 0.3,
    not invented, f"invented={invented}", fatal=True,
)

doc_edits = [
    f for f in git(ws, "diff", "--name-only", "HEAD", "--").splitlines()
    if f.startswith("vendor-docs/")
]
r.add("no_doc_edits", "벤더 문서 미수정", 0.2, not doc_edits, f"edited={doc_edits}")
r.emit()
