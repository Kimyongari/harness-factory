"""서버 바인딩 설정."""

from config.store import lookup

DEFAULT_WORKERS = 1


def bind_host() -> str:
    return lookup("server.host", default="127.0.0.1")


def bind_port() -> int:
    return int(lookup("server.port", default=8000))


def worker_count() -> int:
    return int(lookup("server.workers", default=DEFAULT_WORKERS))


def debug_mode() -> bool:
    return lookup("server.debug", default="false") == "true"


def base_url() -> str:
    """프록시 설정·헬스체크가 참조하는 외부 노출 URL."""
    host = lookup("server.host", default="localhost")
    port = lookup("server.port", default=8000)
    return f"http://{host}:{port}/api"
