"""사용자 목록 CLI.

사용: python app.py list [--db PATH]
출력: 한 줄에 "이름<TAB>이메일". 이메일이 없으면 "-".
"""

import argparse
import sqlite3


def _migrated(conn: sqlite3.Connection) -> bool:
    return conn.execute("PRAGMA user_version").fetchone()[0] >= 1


def list_users(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    if _migrated(conn):
        rows = conn.execute(
            "SELECT u.name,"
            " (SELECT value FROM contacts c WHERE c.user_id = u.id AND c.kind = 'email')"
            " FROM users u ORDER BY u.id"
        ).fetchall()
    else:
        rows = conn.execute("SELECT name, email FROM users ORDER BY id").fetchall()
    conn.close()
    return [f"{name}\t{email if email is not None else '-'}" for name, email in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["list"])
    parser.add_argument("--db", default="app.db")
    args = parser.parse_args()
    for line in list_users(args.db):
        print(line)


if __name__ == "__main__":
    main()
