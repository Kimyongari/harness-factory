"""보이는 테스트 — 각 설정 함수의 현재 동작."""

from app.cache import backend, ttl_seconds
from app.http_client import timeout_seconds, user_agent
from app.logging_setup import audit_enabled, log_level
from app.server import bind_host, bind_port, debug_mode, worker_count


def test_bind_host():
    assert bind_host() == "0.0.0.0"


def test_bind_port():
    assert bind_port() == 8080


def test_worker_count():
    assert worker_count() == 4


def test_debug_mode_off():
    assert debug_mode() is False


def test_timeout_seconds():
    assert timeout_seconds() == 2.5


def test_user_agent():
    assert user_agent() == "svc-client/2.1"


def test_cache_ttl():
    assert ttl_seconds() == 300


def test_cache_backend():
    assert backend() == "memory"


def test_log_level():
    assert log_level() == "INFO"


def test_audit_enabled():
    assert audit_enabled() is True
