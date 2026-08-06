"""서버 바인딩 설정."""

from config.legacy import get

DEFAULT_WORKERS = 1


def bind_host() -> str:
    return get("server", "host", "127.0.0.1")


def bind_port() -> int:
    return int(get("server", "port", "8000"))


def worker_count() -> int:
    return int(get("server", "workers", str(DEFAULT_WORKERS)))


def debug_mode() -> bool:
    return get("server", "debug", "false") == "true"


def base_url() -> str:
    """프록시 설정·헬스체크가 참조하는 외부 노출 URL."""
    host = get("server", "host", "localhost")
    port = get("server", "port", "8000")
    return "http://" + host + ":" + port + "/api"
