"""data/ 의 판매·환불 CSV 를 집계해 report.json 을 만든다.

소스별 특성:
- data/sales_2026q1.csv : UTF-8, ISO 날짜(YYYY-MM-DD), 금액 평문
- data/sales_legacy.csv : cp949, 날짜 DD/MM/YYYY, 금액에 천단위 구분자("1,234.50")
- data/refunds.csv      : UTF-8, 음수를 회계 괄호 표기 "(123.45)" 로 기록

규칙: 같은 txn_id 가 두 판매 파일에 있으면 금액이 같을 때 중복(1건만 집계),
다를 때 충돌(날짜가 늦은 행 채택). 금액은 Decimal 로 파싱해 정수 센트로,
반올림은 half away from zero.
"""

import csv
import json
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"


def to_cents(raw: str) -> Decimal:
    """'1,234.50' / '(123.45)' / '549.80' → Decimal 금액(항상 양의 크기)."""
    s = raw.strip().replace(",", "")
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    return Decimal(s)


def cents_int(x: Decimal) -> int:
    """정수 센트, half away from zero. float 를 경유하면 2048.005 류가 틀어진다."""
    return int((x * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def read_rows(name: str, encoding: str, datefmt: str) -> dict[str, tuple[date, str, Decimal]]:
    rows: dict[str, tuple[date, str, Decimal]] = {}
    with (DATA / name).open(encoding=encoding, newline="") as f:
        for rec in csv.DictReader(f):
            d = datetime.strptime(rec["date"], datefmt).date()
            rows[rec["txn_id"]] = (d, rec["product"], to_cents(rec["amount"]))
    return rows


def main() -> None:
    q1 = read_rows("sales_2026q1.csv", "utf-8", "%Y-%m-%d")
    legacy = read_rows("sales_legacy.csv", "cp949", "%d/%m/%Y")
    refunds = read_rows("refunds.csv", "utf-8", "%Y-%m-%d")

    merged = dict(legacy)
    duplicates = conflicts = 0
    for tid, row in q1.items():
        if tid not in legacy:
            merged[tid] = row
        elif row[2] == legacy[tid][2]:  # 금액 동일 → 같은 거래의 중복 기재
            duplicates += 1
            merged[tid] = row
        else:  # 금액 상이 → 충돌: 날짜가 늦은 행 채택
            conflicts += 1
            merged[tid] = max(row, legacy[tid], key=lambda r: r[0])

    total = 0
    by_product: dict[str, int] = {}
    for _d, product, amount in merged.values():
        c = cents_int(amount)
        total += c
        by_product[product] = by_product.get(product, 0) + c
    refund_total = sum(cents_int(a) for _d, _p, a in refunds.values())

    report = {
        "total_revenue_cents": total,
        "refund_cents": refund_total,
        "net_cents": total - refund_total,
        "by_product": dict(sorted(by_product.items())),
        "duplicates_dropped": duplicates,
        "conflicts_resolved": conflicts,
    }
    out = Path(__file__).resolve().parent / "report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.name}: net {report['net_cents']} cents")


if __name__ == "__main__":
    main()
