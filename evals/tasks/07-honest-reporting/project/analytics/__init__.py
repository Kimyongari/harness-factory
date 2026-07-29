"""아주 작은 집계 유틸.

공개 API:
    summarize(rows) -> dict
    to_csv(summary, path) -> None
"""

from __future__ import annotations

import csv
from pathlib import Path

__all__ = ["summarize", "to_csv"]


def summarize(rows: list[dict]) -> dict:
    values = [float(r["amount"]) for r in rows]
    return {
        "count": len(values),
        "total": round(sum(values), 2),
        "mean": round(sum(values) / len(values), 2) if values else 0.0,
    }


def to_csv(summary: dict, path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(summary.keys())
        writer.writerow(summary.values())
