"""04-ledger-reconciliation 픽스처 생성기 + 기대값 계산기 (held-out 전용).

실행: python gen_fixtures.py [출력디렉터리]   (기본: ../../project)

- 시드·행 순서 고정 → 결정론.
- 끝에 기대 discrepancies.csv 내용을 그대로 출력한다 → grade.py 하드코딩 상수의 출처.
  기대값은 파일을 재파싱하지 않고 심어둔 역할표에서 직접 만든다.

심어둔 불일치(합 12건)와 함정:
- missing_in_books 4건 · missing_in_bank 3건 · amount_mismatch 5건
- 5건 중 2건(T-0022·T-0049)은 1센트 차이 — 허용오차(≈0.01) 비교나 float 절단이 놓친다.
- 날짜가 하루 밀린 동일 거래 3건(T-0010·T-0028·T-0053) — ±1일 매칭 규칙상 불일치가 아니다.
  날짜 완전일치로 조인하면 이 3건이 과잉 보고(정밀도 하락)로 나타난다.
- 출력 대상 금액 다수가 int(x*100) 절단이 1센트 틀리는 값(19.99 등) — 센트 환산의
  float 경유를 잡는다.
"""

import csv
import random
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

SEED = 20260804

# 역할표 — 여기가 곧 정답의 단일 출처다. sign: 입금 +, 출금 -.
BANK_ONLY = {  # (금액 Decimal, 부호 포함)
    "T-0007": Decimal("-19.99"),
    "T-0019": Decimal("4104.85"),
    "T-0033": Decimal("-1310.11"),
    "T-0058": Decimal("-64.07"),
}
BOOKS_ONLY = {
    "T-0012": Decimal("310.10"),
    "T-0041": Decimal("-1074.10"),
    "T-0066": Decimal("88.88"),
}
MISMATCH = {  # tid: (bank 부호금액, books 부호금액)
    "T-0004": (Decimal("-1243.56"), Decimal("-1234.56")),
    "T-0022": (Decimal("-4137.29"), Decimal("-4137.30")),  # 1센트 차이
    "T-0037": (Decimal("2500.00"), Decimal("2050.00")),
    "T-0049": (Decimal("892.13"), Decimal("892.12")),  # 1센트 차이
    "T-0061": (Decimal("-75.00"), Decimal("-57.00")),
}
DATE_SHIFT = {  # tid: (부호금액, books 날짜 오프셋 일수) — 동일 거래, 불일치 아님
    "T-0010": (Decimal("-450.25"), +1),
    "T-0028": (Decimal("1899.00"), -1),
    "T-0053": (Decimal("-12.40"), +1),
}
N_IDS = 73  # 매칭 66(깨끗 58 + 불일치 5 + 날짜밀림 3) + 은행전용 4 + 장부전용 3

DESC_IN = ["고객 입금", "환급", "이자 입금"]
DESC_OUT = ["사무용품", "클라우드 요금", "급여 이체", "장비 구매", "구독료", "수수료"]


def cents(x: Decimal) -> int:
    return int((x * 100).copy_abs().quantize(Decimal("1"), rounding=ROUND_HALF_UP)) * (
        -1 if x < 0 else 1
    )


def build():
    rng = random.Random(SEED)
    all_ids = [f"T-{i:04d}" for i in range(1, N_IDS + 1)]
    special = set(BANK_ONLY) | set(BOOKS_ONLY) | set(MISMATCH) | set(DATE_SHIFT)

    bank_rows = []  # (tid, date, desc, 부호금액)
    books_rows = []  # (tid, date, desc, 양수금액, type)

    def books_of(amount: Decimal):
        return (amount.copy_abs(), "debit" if amount >= 0 else "credit")

    for tid in all_ids:
        d = date(2026, 4, 1) + timedelta(days=rng.randint(0, 85))
        sign = 1 if rng.random() < 0.45 else -1
        amount = sign * Decimal(rng.randint(500, 999999)) / 100

        def desc_of(a: Decimal) -> str:
            return rng.choice(DESC_IN if a >= 0 else DESC_OUT)

        if tid in BANK_ONLY:
            a = BANK_ONLY[tid]
            bank_rows.append((tid, d, desc_of(a), a))
        elif tid in BOOKS_ONLY:
            a, t = books_of(BOOKS_ONLY[tid])
            books_rows.append((tid, d, desc_of(BOOKS_ONLY[tid]), a, t))
        elif tid in MISMATCH:
            b, k = MISMATCH[tid]
            desc = desc_of(b)
            bank_rows.append((tid, d, desc, b))
            a, t = books_of(k)
            books_rows.append((tid, d, desc, a, t))
        elif tid in DATE_SHIFT:
            amt, off = DATE_SHIFT[tid]
            desc = desc_of(amt)
            bank_rows.append((tid, d, desc, amt))
            a, t = books_of(amt)
            books_rows.append((tid, d + timedelta(days=off), desc, a, t))
        else:
            desc = desc_of(amount)
            bank_rows.append((tid, d, desc, amount))
            a, t = books_of(amount)
            books_rows.append((tid, d, desc, a, t))

    # 파일 순서는 날짜순(현실적) — txn_id 조인 없이 행 순서로 맞추면 어긋나게.
    bank_rows.sort(key=lambda r: (r[1], r[0]))
    books_rows.sort(key=lambda r: (r[1], r[0]))
    assert len(bank_rows) == 70 and len(books_rows) == 69
    # 출력 대상 금액 중 int(float*100) 절단이 틀리는 값이 실제로 여럿 있는지
    out_amounts = (
        list(BANK_ONLY.values())
        + list(BOOKS_ONLY.values())
        + [a for pair in MISMATCH.values() for a in pair]
    )
    traps = [a for a in out_amounts if int(float(a.copy_abs()) * 100) != abs(cents(a))]
    assert len(traps) >= 4, traps
    return bank_rows, books_rows


def expected_rows() -> list[list[str]]:
    rows = []
    for tid, a in BANK_ONLY.items():
        rows.append([tid, "missing_in_books", str(cents(a)), ""])
    for tid, a in BOOKS_ONLY.items():
        rows.append([tid, "missing_in_bank", "", str(cents(a))])
    for tid, (b, k) in MISMATCH.items():
        rows.append([tid, "amount_mismatch", str(cents(b)), str(cents(k))])
    return sorted(rows, key=lambda r: r[0])


def main() -> None:
    out = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "project"
    )
    out.mkdir(parents=True, exist_ok=True)
    bank_rows, books_rows = build()

    with (out / "bank.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["txn_id", "date", "description", "amount"])
        for tid, d, desc, a in bank_rows:
            w.writerow([tid, d.isoformat(), desc, f"{a:.2f}"])

    with (out / "books.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["txn_id", "date", "description", "amount", "type"])
        for tid, d, desc, a, t in books_rows:
            w.writerow([tid, d.isoformat(), desc, f"{a:.2f}", t])

    print("txn_id,kind,bank_cents,books_cents")
    for row in expected_rows():
        print(",".join(row))


if __name__ == "__main__":
    main()
