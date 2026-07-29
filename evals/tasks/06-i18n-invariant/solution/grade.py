import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()
GATES = {"key_added_ko"}
for cid, label, weight, expr in [
    ("keys_in_sync", "ko/en 키 집합 동일", 0.35, "keys_in_sync"),
    ("key_added_ko", "ko 에 save_failed 추가", 0.2, "key_added_ko"),
    ("key_added_en", "en 에 save_failed 추가", 0.2, "key_added_en"),
    ("en_is_english", "en 값이 실제 영어", 0.15, "en_value_is_english"),
    ("pass_to_pass", "기존 키 회귀 없음", 0.1, "pass_to_pass"),
]:
    ok, log = run_heldout(ws, HELDOUT, expr=expr)
    r.add(cid, label, weight, ok, log if not ok else "", gate=cid in GATES)
r.emit()
