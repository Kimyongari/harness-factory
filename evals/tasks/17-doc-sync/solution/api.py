"""사용자 조회 API."""

from __future__ import annotations

USERS = [
    {"id": 1, "name": "alice", "email": "alice@example.com"},
    {"id": 2, "name": "bob", "email": "bob@example.com"},
]


def get_user(user_id: int | None = None, email: str | None = None) -> dict | None:
    """id 또는 email 로 사용자를 찾는다. 둘 다 없으면 None."""
    for user in USERS:
        if user_id is not None and user["id"] == user_id:
            return user
        if email is not None and user["email"] == email:
            return user
    return None
