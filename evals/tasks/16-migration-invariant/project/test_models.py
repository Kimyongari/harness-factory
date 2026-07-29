import sqlite3

from db import apply_migrations, columns
from models import FIELDS, TABLE


def test_schema_matches_model():
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    assert columns(conn, TABLE) == FIELDS
