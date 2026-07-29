"""사용자 조회 API."""

from __future__ import annotations

USERS = [
    {"id": 1, "name": "alice", "email": "alice@example.com"},
    {"id": 2, "name": "bob", "email": "bob@example.com"},
]


def get_user(user_id: int) -> dict | None:
    """id 로 사용자를 찾는다."""
    for user in USERS:
        if user["id"] == user_id:
            return user
    return None
