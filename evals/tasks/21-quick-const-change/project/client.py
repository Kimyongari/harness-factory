"""외부 API 호출 클라이언트."""

import urllib.request

REQUEST_TIMEOUT = 30  # 초
MAX_RETRIES = 3
USER_AGENT = "demo-client/1.0"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return resp.read()
