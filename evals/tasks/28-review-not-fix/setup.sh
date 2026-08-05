#!/usr/bin/env bash
# 리뷰 대상 커밋을 만든다 — 결함 두 개를 담아서.
set -euo pipefail
cd "$1"
cat >> store.py <<'PY'


def find_by_name(conn, name: str):
    """이름으로 사용자를 찾는다."""
    cur = conn.execute(f"SELECT * FROM users WHERE name = '{name}'")
    return cur.fetchall()


def first_email(conn, name: str) -> str:
    """검색 결과 중 첫 사용자의 이메일."""
    rows = find_by_name(conn, name)
    return rows[0][2]
PY
git add store.py
git -c user.email=dev@example.com -c user.name=dev \
    -c core.hooksPath=/dev/null commit -q -m "feat(store): 이름으로 사용자 조회 추가"
