"""held-out: 모델과 실제 적용 스키마가 일치하는지 새 DB 에 마이그레이션을 돌려 확인한다."""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _applied_columns():
    from db import apply_migrations, columns
    from models import TABLE

    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    try:
        return columns(conn, TABLE)
    finally:
        conn.close()


def test_model_declares_phone():
    from models import FIELDS

    assert "phone" in FIELDS, "models.FIELDS 에 phone 이 없다"


def test_schema_has_phone():
    assert "phone" in _applied_columns(), "마이그레이션이 phone 컬럼을 만들지 않는다"


def test_schema_matches_model():
    from models import FIELDS

    assert sorted(_applied_columns()) == sorted(FIELDS), (
        f"스키마 불일치 — 적용됨:{_applied_columns()} 모델:{FIELDS}"
    )


def test_existing_columns_intact():
    cols = _applied_columns()
    for name in ("id", "name", "email"):
        assert name in cols, f"기존 컬럼 {name} 이 사라졌다"
