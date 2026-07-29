import pytest

from schema_client import fetch_schema
from slug import slugify


def test_slugify_lowercases():
    assert slugify("Hello") == "hello"


def test_slugify_replaces_spaces():
    assert slugify("Hello World") == "hello-world"


@pytest.mark.skipif(True, reason="네트워크 차단 환경에서는 원격 스키마를 조회할 수 없다")
def test_remote_schema():
    """원격 스키마와 필드가 맞는지 확인한다(네트워크 필요)."""
    schema = fetch_schema()
    assert schema["type"] == "slug"
