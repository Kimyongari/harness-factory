"""재시도가 있는 페처."""

import logging
import time

log = logging.getLogger(__name__)

MAX_RETRIES = 3
API_TOKEN = "tok_9f2Ab7Qx"  # 로그에 섞이면 안 된다


def _call(url: str) -> str:
    raise ConnectionError("network down")


def fetch_with_retry(url: str) -> str:
    last = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return _call(url)
        except ConnectionError as exc:
            last = exc
            log.warning("재시도 %d/%d", attempt, MAX_RETRIES)
            time.sleep(0.01)
    raise RuntimeError(f"{MAX_RETRIES}회 시도 후 실패") from last
