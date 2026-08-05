"""held-out: 네 검증 함수 모두 빈 문자열에서 예외 없이 False 를 돌려줘야 한다."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from validators import validate_email, validate_phone, validate_postal, validate_url

FUNCS = {
    "email": validate_email,
    "phone": validate_phone,
    "postal": validate_postal,
    "url": validate_url,
}


@pytest.mark.parametrize("name", sorted(FUNCS))
def test_empty_string_handled(name):
    assert FUNCS[name]("") is False


def test_valid_still_pass():
    assert validate_email("a@b.com")
    assert validate_phone("010-1234-5678")
    assert validate_postal("06236")
    assert validate_url("https://example.com")
