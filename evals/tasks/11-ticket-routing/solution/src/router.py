"""티켓 라우팅 엔진 — POLICY.md 제1~12조의 골든 구현."""

from datetime import datetime, time, timedelta

_CATEGORY_QUEUES = {
    "billing": "finance",
    "technical": "tech-support",
    "account": "account-ops",
}
_INTL_LANGS = {"ja", "zh"}
_ATTACH_LIMIT_BYTES = 10_485_760
_KST_OFFSET = timedelta(hours=9)


def _norm(value) -> str:
    """제1조 3항: 대소문자·앞뒤 공백 무시."""
    return str(value or "").strip().lower()


def _kst(created_utc: str) -> datetime:
    """제1조: UTC ISO 8601(`Z` 또는 `+00:00`)을 KST naive datetime 으로."""
    raw = created_utc.strip()
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is not None:
        parsed = (parsed - parsed.utcoffset()).replace(tzinfo=None)
    return parsed + _KST_OFFSET


def _in_business_hours(created_utc: str) -> bool:
    """제5조: 평일 09:00:00 이상 18:00:00 미만(KST)."""
    kst = _kst(created_utc)
    return kst.weekday() < 5 and time(9, 0) <= kst.time() < time(18, 0)


def _language_root(ticket: dict) -> str:
    """제4조: 지역 표기는 하이픈 앞부분 기준."""
    return _norm(ticket.get("language")).split("-", 1)[0]


def _attachment_total(ticket: dict) -> int:
    return sum(int(item.get("size_bytes", 0)) for item in ticket.get("attachments") or [])


def route(ticket: dict) -> str:
    """티켓을 받아 POLICY.md 에 정의된 큐 이름을 돌려준다."""
    # 제8조: urgent 는 모든 조항에 우선.
    if _norm(ticket.get("priority")) == "urgent":
        return "escalation"

    # 제6·7조: VIP (영업시간 규칙 미적용). billing 이면 예외의 예외.
    if bool(ticket.get("vip")):
        if _norm(ticket.get("subject_category")) == "billing":
            return "finance-priority"
        return "vip"

    # 제5조: 영업시간 외는 다음 영업일 큐.
    if not _in_business_hours(ticket["created_utc"]):
        return "next-business-day"

    # 제4조: 언어.
    if _language_root(ticket) in _INTL_LANGS:
        return "intl"

    # 제3조: 첨부 크기 초과.
    if _attachment_total(ticket) > _ATTACH_LIMIT_BYTES:
        return "large-files"

    # 제2조: 기본 라우팅.
    return _CATEGORY_QUEUES.get(_norm(ticket.get("subject_category")), "general")
