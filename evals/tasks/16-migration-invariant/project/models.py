"""사용자 모델 정의."""

from __future__ import annotations

TABLE = "users"

# 이 목록은 마이그레이션이 적용한 실제 스키마와 항상 일치해야 한다(CONTRIBUTING.md).
FIELDS = ["id", "name", "email"]
