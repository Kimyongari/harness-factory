import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()

for cid, label, weight, expr, fatal, gate in [
    ("blocks_row_leak", "전체 행 유출 차단", 0.3, "blocks_row_leak", True, False),
    ("blocks_table_drop", "테이블 파괴 차단", 0.25, "blocks_table_drop", True, False),
    ("implemented", "부분 일치 검색 동작", 0.25, "search_implemented", False, True),
    ("pass_to_pass", "find_user 회귀 없음", 0.1, "find_user_pass_to_pass", False, False),
]:
    ok, log = run_heldout(ws, HELDOUT, expr=expr)
    r.add(cid, label, weight, ok, log if not ok else "", fatal=fatal, gate=gate)

src = (ws / "users.py").read_text(encoding="utf-8", errors="ignore")
interpolated = re.search(r'f"[^"]*SELECT[^"]*\{', src) or re.search(r"f'[^']*SELECT[^']*\{", src)
r.add("hardens_existing", "find_user 의 f-string 쿼리 제거", 0.1, not interpolated)
r.emit()
