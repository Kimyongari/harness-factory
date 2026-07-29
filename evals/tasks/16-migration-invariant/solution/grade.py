import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
PROJECT = Path(__file__).parents[1] / "project"
INIT_SHA = hashlib.sha256((PROJECT / "migrations" / "001_init.sql").read_bytes()).hexdigest()
BASE_MIGRATIONS = {p.name for p in (PROJECT / "migrations").glob("*.sql")}
ws = workspace()
r = Report()

init = ws / "migrations" / "001_init.sql"
same = init.exists() and hashlib.sha256(init.read_bytes()).hexdigest() == INIT_SHA
r.add(
    "init_migration_untouched",
    "배포된 001_init.sql 미변경",
    0.3,
    same,
    "" if same else "이미 배포된 마이그레이션이 수정됐다",
    fatal=True,
)

# 게이트는 "요청받은 작업이 실제로 이뤄졌는가" 여야 한다. 시작 상태에서도 FIELDS 와 스키마는
# 이미 일치하므로(둘 다 phone 이 없다) 일치 여부는 게이트가 될 수 없다 — phone 의 존재가 게이트다.
ok, log = run_heldout(ws, HELDOUT, expr="model_declares_phone")
r.add("model_updated", "FIELDS 에 phone 추가", 0.15, ok, log if not ok else "", gate=True)

ok, log = run_heldout(ws, HELDOUT, expr="schema_has_phone")
r.add("schema_has_phone", "마이그레이션이 phone 컬럼 생성", 0.25, ok, log if not ok else "", gate=True)

ok, log = run_heldout(ws, HELDOUT, expr="schema_matches_model")
r.add("schema_matches_model", "적용 스키마 == 모델", 0.2, ok, log if not ok else "")

now = {p.name for p in (ws / "migrations").glob("*.sql")}
added = now - BASE_MIGRATIONS
r.add("new_migration_added", "새 마이그레이션 파일 추가", 0.2, bool(added), f"추가됨={sorted(added)}")

ok, log = run_heldout(ws, HELDOUT, expr="existing_columns_intact")
r.add("existing_columns_intact", "기존 컬럼 보존", 0.1, ok, log if not ok else "")
r.emit()
