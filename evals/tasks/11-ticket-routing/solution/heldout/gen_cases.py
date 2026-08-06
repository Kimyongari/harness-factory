"""heldout 케이스 40개 생성기 — 기대값은 골든 구현으로 산출해 cases.json 에 하드코딩한다.

재생성: `python gen_cases.py` (이 디렉터리에서). 결정론적(입력 고정)이다.
날짜 기준: 2026-08-03(월) ~ 2026-08-10(월). KST = UTC+9.
"""

import importlib.util
import json
import sys
from pathlib import Path

GOLDEN = Path(__file__).resolve().parents[1] / "src" / "router.py"
spec = importlib.util.spec_from_file_location("golden_router", GOLDEN)
golden = importlib.util.module_from_spec(spec)
spec.loader.exec_module(golden)

BUSINESS = "2026-08-05T05:00:00Z"  # 수 14:00 KST
WEEKEND = "2026-08-08T03:00:00Z"  # 토 12:00 KST


def t(tid, **overrides):
    base = {
        "id": tid,
        "subject_category": "technical",
        "priority": "normal",
        "vip": False,
        "language": "en",
        "created_utc": BUSINESS,
    }
    base.update(overrides)
    return base


BIG = [{"name": "dump.bin", "size_bytes": 10_485_761}]

CASES = [
    # ---- gate: 보이는 테스트와 같은 난이도(단일 규칙) 6개 ------------------
    ("gate", t("G1")),
    ("gate", t("G2", subject_category="billing")),
    ("gate", t("G3", subject_category="account")),
    ("gate", t("G4", priority="urgent")),
    ("gate", t("G5", vip=True)),
    ("gate", t("G6", language="ja")),
    # ---- precedence: urgent × VIP × billing 3중 교차 12개 -----------------
    ("precedence", t("P1", vip=True, subject_category="billing", priority="urgent")),
    ("precedence", t("P2", vip=True, subject_category="billing")),
    ("precedence", t("P3", vip=True, subject_category="billing", created_utc=WEEKEND)),
    ("precedence", t("P4", vip=True, created_utc=WEEKEND)),
    ("precedence", t("P5", priority="urgent", created_utc=WEEKEND)),
    ("precedence", t("P6", priority="urgent", language="ja")),
    ("precedence", t("P7", vip=True, language="ja")),
    ("precedence", t("P8", vip=True, subject_category="billing", language="zh")),
    ("precedence", t("P9", priority="urgent", subject_category="billing")),
    ("precedence", t("P10", priority="URGENT")),
    ("precedence", t("P11", vip=True, subject_category="parking")),
    ("precedence", t("P12", vip=True, attachments=BIG)),
    # ---- time: KST 변환·영업시간 경계 12개 --------------------------------
    ("time", t("T1", created_utc="2026-08-07T08:59:00Z")),  # 금 17:59 KST
    ("time", t("T2", created_utc="2026-08-07T09:00:00Z")),  # 금 18:00 KST 정각
    ("time", t("T3", created_utc="2026-08-07T08:59:59Z")),  # 금 17:59:59 KST
    ("time", t("T4", created_utc="2026-08-07T15:00:00Z")),  # 토 00:00 KST
    ("time", t("T5", created_utc="2026-08-09T22:30:00Z")),  # 월 07:30 KST
    ("time", t("T6", created_utc="2026-08-10T00:00:00Z")),  # 월 09:00 KST 정각
    ("time", t("T7", created_utc="2026-08-09T23:59:00Z")),  # 월 08:59 KST
    ("time", t("T8", created_utc=WEEKEND)),  # 토 12:00 KST
    ("time", t("T9", created_utc="2026-08-05T23:50:00Z")),  # 목 08:50 KST
    ("time", t("T10", subject_category="billing", created_utc="2026-08-05T05:00:00+00:00")),
    ("time", t("T11", language="ja", created_utc=WEEKEND)),
    ("time", t("T12", attachments=BIG, created_utc=WEEKEND)),
    # ---- misc: 언어 변형·첨부 경계·누락 필드 10개 --------------------------
    ("misc", t("M1", language="zh-TW")),
    ("misc", t("M2", language="JA")),
    ("misc", t("M3", language="ko")),
    ("misc", t("M4", attachments=[{"name": "a.zip", "size_bytes": 10_485_760}])),
    ("misc", t("M5", attachments=BIG)),
    (
        "misc",
        t(
            "M6",
            attachments=[
                {"name": "a.zip", "size_bytes": 6_000_000},
                {"name": "b.zip", "size_bytes": 4_500_000},
            ],
        ),
    ),
    ("misc", t("M7", language="ja", subject_category="billing")),
    ("misc", t("M8", attachments=BIG, subject_category="billing")),
    ("misc", {"id": "M9", "subject_category": "returns", "created_utc": BUSINESS}),
    ("misc", t("M10", subject_category="Billing")),
]


def main() -> None:
    out = []
    for group, ticket in CASES:
        out.append(
            {
                "id": ticket["id"],
                "group": group,
                "ticket": ticket,
                "expected": golden.route(dict(ticket)),
            }
        )
    dest = Path(__file__).parent / "cases.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(out)} cases -> {dest}")


if __name__ == "__main__":
    sys.exit(main())
