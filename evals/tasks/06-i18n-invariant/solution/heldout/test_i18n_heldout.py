"""held-out: 불변식(키 집합 동등)과 신규 키를 양쪽 로케일에서 검증한다."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LOCALES = ROOT / "locales"


def _load(lang):
    return json.loads((LOCALES / f"messages.{lang}.json").read_text(encoding="utf-8"))


def test_key_added_ko():
    assert _load("ko").get("save_failed") == "저장에 실패했습니다"


def test_key_added_en():
    assert "save_failed" in _load("en"), "en 로케일에 save_failed 가 없다"


def test_keys_in_sync():
    ko, en = set(_load("ko")), set(_load("en"))
    assert ko == en, f"키 집합 불일치 — ko-only:{sorted(ko - en)} en-only:{sorted(en - ko)}"


def test_en_value_is_english():
    value = _load("en").get("save_failed", "")
    has_hangul = any("가" <= ch <= "힣" for ch in value)
    assert value and not has_hangul, f"en 값이 영어가 아니다: {value!r}"


def test_existing_keys_pass_to_pass():
    ko = _load("ko")
    assert ko["save_ok"] == "저장했습니다" and ko["not_found"] == "찾을 수 없습니다"
