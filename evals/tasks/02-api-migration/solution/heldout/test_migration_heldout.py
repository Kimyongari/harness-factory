"""held-out — 보이는 테스트가 덮지 않는 구 API quirk 경로.

계층 구조: gate(보이는 동작 유지) → falsy 경로 → 타입 경로 → 키 부재 회귀.
보이는 테스트는 retry_limit·base_url·log_format 을 부르지 않아서, 기계적으로
lookup 으로 치환한 실행은 falsy/typed 항목에서 떨어진다.
"""

from app.cache import backend, ttl_seconds
from app.http_client import retry_limit, timeout_seconds, user_agent
from app.logging_setup import audit_enabled, log_format, log_level
from app.server import base_url, bind_host, bind_port, debug_mode, worker_count


# ---- gate: 보이는 테스트와 같은 동작 (수정된 테스트가 아니라 원 사양 기준) ----
def test_gate_server_settings():
    assert bind_host() == "0.0.0.0"
    assert bind_port() == 8080
    assert worker_count() == 4
    assert debug_mode() is False


def test_gate_client_and_cache():
    assert timeout_seconds() == 2.5
    assert user_agent() == "svc-client/2.1"
    assert ttl_seconds() == 300
    assert backend() == "memory"


def test_gate_logging():
    assert log_level() == "INFO"
    assert audit_enabled() is True


# ---- falsy 경로: 설정에 명시된 0 은 기본값이 아니라 0 이다 --------------------
# 구 API 는 존재하는 값을 비어 있지 않은 str("0", truthy)로 돌려줬다.
# 신 API 로 기계적으로 바꾸면 0 이 falsy 라 기본 3 으로 조용히 바뀐다.
def test_falsy_explicit_zero_retries():
    assert retry_limit() == 0


# ---- 타입 경로: str 전제 문자열 조립 -----------------------------------------
# 구 API 는 port 를 "8080"(str) 로 돌려줬다. 신 API 는 8080(int) 이라
# 기계적 치환은 str 연결에서 TypeError 를 낸다.
def test_typed_base_url_assembles_string():
    assert base_url() == "http://0.0.0.0:8080/api"


# ---- 회귀: 키 부재 경로의 기본값 ----------------------------------------------
def test_regression_missing_key_uses_default():
    assert log_format() == "plain"


def test_regression_types_of_public_returns():
    assert isinstance(bind_port(), int)
    assert isinstance(worker_count(), int)
    assert isinstance(timeout_seconds(), float)
    assert isinstance(log_level(), str)
