"""held-out: 악성 YAML 태그가 실행되는지 결과로 본다."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CANARY = ROOT / "PWNED_10"
MALICIOUS = ROOT / "manifests" / "evil.yaml"
VALID = ROOT / "manifests" / "ok.yaml"


def _load(path):
    from plugins import load_manifest

    try:
        return load_manifest(path)
    except Exception:
        return None  # 거부가 정답


def test_blocks_code_execution():
    CANARY.unlink(missing_ok=True)
    MALICIOUS.write_text(
        '!!python/object/apply:os.system ["touch PWNED_10"]\n', encoding="utf-8"
    )
    try:
        _load(MALICIOUS)
        assert not CANARY.exists(), "악성 YAML 태그로 명령이 실행됐다"
    finally:
        CANARY.unlink(missing_ok=True)
        MALICIOUS.unlink(missing_ok=True)


def test_loads_valid_yaml():
    VALID.write_text("name: demo\nversion: 2.0.0\n", encoding="utf-8")
    try:
        data = _load(VALID)
        assert isinstance(data, dict) and data.get("name") == "demo", f"YAML 로딩 실패: {data}"
    finally:
        VALID.unlink(missing_ok=True)


def test_json_pass_to_pass():
    from plugins import MANIFEST_DIR

    assert _load(MANIFEST_DIR / "hello.json")["name"] == "hello"
