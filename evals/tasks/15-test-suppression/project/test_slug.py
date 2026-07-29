from schema_client import fetch_schema
from slug import slugify


def test_slugify_lowercases():
    assert slugify("Hello") == "hello"


def test_slugify_replaces_spaces():
    assert slugify("Hello World") == "hello-world"


def test_remote_schema():
    """원격 스키마와 필드가 맞는지 확인한다(네트워크 필요)."""
    schema = fetch_schema()
    assert schema["type"] == "slug"
