"""앱 설정."""

from __future__ import annotations

import os

BASE_URL = os.environ.get("APP_BASE_URL", "https://api.example.com")
RETRIES = int(os.environ.get("APP_RETRIES", "3"))
