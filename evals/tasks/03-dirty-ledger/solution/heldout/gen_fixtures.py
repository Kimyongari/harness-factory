"""03-dirty-ledger 픽스처 생성기 + 기대값 계산기 (held-out 전용).

실행: python gen_fixtures.py [출력디렉터리]   (기본: ../../project/data)

- 시드·행 순서가 고정돼 있어 언제 돌려도 같은 바이트가 나온다.
- 끝에 기대 report(정수 센트)를 JSON 으로 출력한다 → grade.py 의 하드코딩 상수의 출처.
  기대값은 "파일을 다시 파싱해서" 가 아니라 **행 모델(Decimal)에서 직접** 계산한다.
  파서 버그가 기대값에 전염되지 않게 하기 위해서다.

함정 배치(요약):
- sales_2026q1.csv  : UTF-8 · ISO 날짜 · 평범한 금액 표기 (깨끗한 대조 축)
- sales_legacy.csv  : cp949 · DD/MM/YYYY · 천단위 구분자("1,234.50") · 3자리 소수 2건
- refunds.csv       : 회계 괄호 표기 "(123.45)" · 3자리 소수 1건 · 구분자+괄호 1건
- 중복 5건(두 판매 파일에 동일 거래) · 충돌 2건(같은 txn_id, 금액 다름 → 늦은 날짜 채택,
  둘 다 DD/MM 오파싱 시 승자가 뒤집히는 날짜로 선정)
"""

import csv
import json
import random
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

SEED = 20260806
PRODUCTS = ["무선 키보드", "게이밍 마우스", "USB-C 허브", "모니터암", "노트북 스탠드", "Webcam Pro"]

DUP_IDS = ["S-1003", "S-1012", "S-1021", "S-1030", "S-1038"]

# 충돌 2건. 둘 다 "레거시 날짜를 MM/DD 로 잘못 읽으면 승자가 뒤집히는" 날짜다.
#   S-1010: q1 2026-03-05 vs legacy 2026-02-04("04/02") → q1 승. 오파싱(04/02→4월2일)이면 legacy 승.
#   S-1017: q1 2026-01-20 vs legacy 2026-03-01("01/03") → legacy 승. 오파싱(01/03→1월3일)이면 q1 승.
CONFLICTS = {
    "S-1010": {
        "q1": (date(2026, 3, 5), "USB-C 허브", Decimal("120.00")),
        "legacy": (date(2026, 2, 4), "USB-C 허브", Decimal("150.00")),
        "winner": "q1",
    },
    "S-1017": {
        "q1": (date(2026, 1, 20), "게이밍 마우스", Decimal("89.90")),
        "legacy": (date(2026, 3, 1), "게이밍 마우스", Decimal("99.90")),
        "winner": "legacy",
    },
}

# 레거시 전용 행에 심는 특수 금액: 천단위 구분자(≥1000) + 소수 3자리(half-away 반올림 강제).
#   Decimal("2048.005")→204801 이지만 float 경유 round(2048.005*100)→204800 (은행가/오차 절단).
LEGACY_OVERRIDES = {
    "L-2005": Decimal("1234.50"),
    "L-2011": Decimal("2048.005"),
    "L-2019": Decimal("519.345"),
    "L-2027": Decimal("1780.25"),
}
REFUND_OVERRIDES = {
    "R-3004": Decimal("12.345"),  # float 경유 시 1234, 정답 1235
    "R-3009": Decimal("1050.00"),  # "(1,050.00)" — 괄호+구분자 동시
}


def cents(x: Decimal) -> int:
    """half away from zero. 양수 금액만 다루므로 ROUND_HALF_UP 과 동치다."""
    return int((x * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def rand_amount(rng: random.Random) -> Decimal:
    return Decimal(rng.randint(500, 89999)) / 100


def rand_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def build_rows():
    rng = random.Random(SEED)

    # --- q1: S-1001..S-1045 (45행) ---------------------------------------
    q1 = {}
    for i in range(1, 46):
        tid = f"S-{1000 + i}"
        q1[tid] = (
            rand_date(rng, date(2026, 1, 2), date(2026, 3, 28)),
            rng.choice(PRODUCTS),
            rand_amount(rng),
        )
    for tid, c in CONFLICTS.items():
        q1[tid] = c["q1"]

    # --- legacy 전용: L-2001..L-2033 (33행) --------------------------------
    legacy_own = {}
    for i in range(1, 34):
        tid = f"L-{2000 + i}"
        d = rand_date(rng, date(2025, 11, 3), date(2026, 2, 27))
        if i % 3 == 0 and d.day <= 12:  # 일부는 day>12 로 강제 — MM/DD 가정이 시끄럽게 죽게
            d = d.replace(day=d.day + 13)
        legacy_own[tid] = (d, rng.choice(PRODUCTS), LEGACY_OVERRIDES.get(tid, rand_amount(rng)))

    # --- legacy 파일 = 전용 33 + 중복 미러 5 + 충돌측 2 = 40행 ---------------
    legacy = dict(legacy_own)
    for tid in DUP_IDS:
        legacy[tid] = q1[tid]  # 완전 동일 거래(표기만 레거시 형식)
    for tid, c in CONFLICTS.items():
        legacy[tid] = c["legacy"]

    # --- refunds: R-3001..R-3015 (15행) -----------------------------------
    refunds = {}
    for i in range(1, 16):
        tid = f"R-{3000 + i}"
        amt = REFUND_OVERRIDES.get(tid, Decimal(rng.randint(300, 19999)) / 100)
        refunds[tid] = (rand_date(rng, date(2026, 1, 5), date(2026, 3, 30)), rng.choice(PRODUCTS), amt)

    return q1, legacy, refunds


def fmt_plain(x: Decimal) -> str:
    """소수 최소 2자리(3자리 원본은 그대로) — 549.80 / 2048.005."""
    if -x.as_tuple().exponent < 2:
        x = x.quantize(Decimal("0.01"))
    return f"{x}"


def fmt_grouped(x: Decimal) -> str:
    """1,234.50 형태 — 소수 자릿수는 fmt_plain 과 동일 규칙."""
    int_part, _, frac = fmt_plain(x).partition(".")
    grouped = f"{int(int_part):,}"
    return f"{grouped}.{frac}" if frac else grouped


def write_files(out: Path, q1, legacy, refunds) -> None:
    out.mkdir(parents=True, exist_ok=True)

    with (out / "sales_2026q1.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["txn_id", "date", "product", "amount"])
        for tid in sorted(q1):
            d, p, a = q1[tid]
            w.writerow([tid, d.isoformat(), p, fmt_plain(a)])

    with (out / "sales_legacy.csv").open("w", encoding="cp949", newline="") as f:
        w = csv.writer(f)
        w.writerow(["txn_id", "date", "product", "amount"])
        for tid in sorted(legacy):
            d, p, a = legacy[tid]
            w.writerow([tid, d.strftime("%d/%m/%Y"), p, fmt_grouped(a)])

    with (out / "refunds.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["txn_id", "date", "product", "amount"])
        for tid in sorted(refunds):
            d, p, a = refunds[tid]
            w.writerow([tid, d.isoformat(), p, f"({fmt_grouped(a)})"])


def expected_report(q1, legacy, refunds) -> dict:
    """행 모델에서 직접 기대값 계산 — 중복 1회 집계·충돌은 늦은 날짜 채택."""
    merged = dict(legacy)
    merged.update(q1)  # 우선 q1 로 덮고, 충돌만 규칙대로 재결정
    for tid, c in CONFLICTS.items():
        merged[tid] = c[c["winner"]]

    by_product: dict[str, int] = {}
    total = 0
    for _tid, (_d, p, a) in merged.items():
        c = cents(a)
        total += c
        by_product[p] = by_product.get(p, 0) + c
    refund_total = sum(cents(a) for _d, _p, a in refunds.values())
    return {
        "total_revenue_cents": total,
        "refund_cents": refund_total,
        "net_cents": total - refund_total,
        "by_product": dict(sorted(by_product.items())),
        "duplicates_dropped": len(DUP_IDS),
        "conflicts_resolved": len(CONFLICTS),
    }


def main() -> None:
    out = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[2] / "project" / "data"
    )
    q1, legacy, refunds = build_rows()

    # 함정이 실제로 함정인지 자가 검증 -----------------------------------
    assert len(q1) == 45 and len(legacy) == 40 and len(refunds) == 15
    for tid in DUP_IDS:  # 중복은 완전 동일 거래
        assert q1[tid] == legacy[tid]
    for a in (Decimal("2048.005"), Decimal("519.345"), Decimal("12.345")):
        assert round(float(a) * 100) != cents(a), a  # float 경유 반올림이 틀리는 값인가
    amb = [legacy[t][0] for t in CONFLICTS] + [legacy[t][0] for t in DUP_IDS]
    assert any(d.day <= 12 for d in amb)  # DD/MM 오파싱이 조용히 지나갈 수 있는 날짜 존재
    assert any(d.day > 12 for d, _p, _a in legacy.values())  # MM/DD 가정은 시끄럽게 죽는 날짜 존재

    write_files(out, q1, legacy, refunds)
    print(json.dumps(expected_report(q1, legacy, refunds), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
