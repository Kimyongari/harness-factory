"""보이는 테스트 — 단일 규칙만 발동하는 기본 케이스."""

from src.router import route

BUSINESS_HOURS = "2026-08-05T05:00:00Z"  # 수요일 14:00 KST


def _ticket(**overrides) -> dict:
    base = {
        "id": "T-1",
        "subject_category": "technical",
        "priority": "normal",
        "vip": False,
        "language": "en",
        "created_utc": BUSINESS_HOURS,
    }
    base.update(overrides)
    return base


def test_basic_technical():
    assert route(_ticket()) == "tech-support"


def test_basic_billing():
    assert route(_ticket(subject_category="billing")) == "finance"


def test_urgent_goes_to_escalation():
    assert route(_ticket(priority="urgent")) == "escalation"


def test_vip_goes_to_vip_queue():
    assert route(_ticket(vip=True)) == "vip"


def test_japanese_goes_to_intl():
    assert route(_ticket(language="ja")) == "intl"
