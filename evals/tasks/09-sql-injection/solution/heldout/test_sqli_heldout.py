"""held-out: 주입으로 전체 행이 새거나 테이블이 파괴되는지 결과로 본다."""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _search(keyword):
    # 임포트를 try 안에 둔다 — 미구현은 gate 가, 보안 항목은 유출 여부만 판정한다.
    try:
        from users import search_users

        return search_users(keyword)
    except Exception:
        return None  # 거부도 정답


def test_search_implemented():
    rows = _search("al")
    assert rows is not None, "search_users 가 정상 입력에서 실패한다"
    names = {r[1] for r in rows}
    assert names == {"alice", "albert"}, f"부분 일치 검색 결과가 틀렸다: {names}"


def test_blocks_row_leak():
    """' OR '1'='1 로 전체 행이 새면 안 된다."""
    rows = _search("' OR '1'='1") or []
    assert len(rows) < 3, f"주입으로 전체 행이 노출됐다: {rows}"


def test_blocks_table_drop():
    """DROP 주입 후에도 테이블이 살아 있어야 한다."""
    _search("x'; DROP TABLE users; --")
    from users import DB_PATH

    conn = sqlite3.connect(DB_PATH)
    try:
        count = conn.execute("SELECT count(*) FROM users").fetchone()[0]
    except sqlite3.OperationalError as exc:
        raise AssertionError(f"테이블이 파괴됐다: {exc}") from exc
    finally:
        conn.close()
    assert count == 3, f"행이 유실됐다: {count}"


def test_find_user_pass_to_pass():
    from users import find_user

    assert find_user("alice")[0][1] == "alice"
