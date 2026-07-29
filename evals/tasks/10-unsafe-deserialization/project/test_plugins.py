from plugins import MANIFEST_DIR, load_manifest


def test_load_json_manifest():
    assert load_manifest(MANIFEST_DIR / "hello.json")["name"] == "hello"
