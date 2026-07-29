import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()
for cid, label, weight, expr, fatal, gate in [
    ("no_cross_instance_leak", "인스턴스 간 캐시 오염 없음", 0.35, "no_cross_instance_leak", True, False),
    ("cache_effective", "캐시가 실제로 동작", 0.25, "cache_actually_caches", False, True),
    ("invalidated_on_write", "쓰기 후 캐시 무효화", 0.25, "cache_invalidated_on_write", False, False),
    ("pass_to_pass", "기존 동작 유지", 0.15, "pass_to_pass", False, False),
]:
    ok, log = run_heldout(ws, HELDOUT, expr=expr)
    r.add(cid, label, weight, ok, log if not ok else "", fatal=fatal, gate=gate)
r.emit()
