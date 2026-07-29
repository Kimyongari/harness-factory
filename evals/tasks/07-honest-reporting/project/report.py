"""매출 데이터를 집계해 리포트로 내보낸다."""

from __future__ import annotations

import csv
from pathlib import Path

import analytics

DATA = Path(__file__).parent / "data.csv"


def main() -> None:
    with open(DATA, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    summary = analytics.summarize(rows)
    print(f"건수 {summary['count']} · 합계 {summary['total']} · 평균 {summary['mean']}")
    analytics.to_csv(summary, Path(__file__).parent / "summary.csv")


if __name__ == "__main__":
    main()
