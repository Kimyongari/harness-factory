#!/usr/bin/env python3
"""06-log-forensics 픽스처 생성기 — project/logs/ 3종과 기대 타임라인을 결정론으로 만든다.

    python3 gen_logs.py <task-dir>

장애 윈도우: 2026-03-14 02:10:00(이상) ~ 02:25:00(미만) UTC.
심는 것: 윈도우 안 수집 대상 18건(app ERROR 6 · gateway 5xx 7 · worker PANIC 5),
윈도우 밖 레드 헤링 6건(app 은 KST 시각을 UTC 로 오독하면 안으로 들어오는 형태 2,
gateway 는 경계 직전/정각 2, worker 는 윈도우 밖 PANIC 2).
"""

import calendar
import csv
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

rng = random.Random(20260314)

WINDOW_START = datetime(2026, 3, 14, 2, 10, 0)
WINDOW_END = datetime(2026, 3, 14, 2, 25, 0)


def utc(h: int, m: int, s: int, day: int = 14) -> datetime:
    return datetime(2026, 3, day, h, m, s)


def iso_z(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def kst_iso(dt_utc: datetime) -> str:
    return (dt_utc + timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%S") + "+09:00"


def epoch(dt_utc: datetime) -> int:
    return calendar.timegm(dt_utc.timetuple())


def nginx_time(dt_utc: datetime) -> str:
    return dt_utc.strftime("%d/%b/%Y:%H:%M:%S +0000")


# --- 수집 대상 (윈도우 안) --------------------------------------------------
APP_ERRORS = [
    (utc(2, 10, 0), "db connection pool exhausted (pool=main)"),
    (utc(2, 12, 41), "checkout failed: upstream timeout"),  # gateway 와 동시각 → 정렬 타이브레이크
    (utc(2, 14, 33), "session store write failed"),
    (utc(2, 17, 5), "payment webhook rejected: signature mismatch"),
    (utc(2, 21, 58), "db connection pool exhausted (pool=replica)"),
    (utc(2, 24, 59), "cart snapshot flush failed"),
]
GATEWAY_5XX = [
    (utc(2, 11, 7), 502, "GET /api/cart HTTP/1.1"),
    (utc(2, 12, 41), 503, "POST /api/checkout HTTP/1.1"),
    (utc(2, 13, 59), 502, "GET /api/products HTTP/1.1"),
    (utc(2, 15, 22), 504, "POST /api/payment HTTP/1.1"),
    (utc(2, 18, 46), 502, "GET /api/session HTTP/1.1"),
    (utc(2, 20, 10), 500, "POST /api/orders HTTP/1.1"),
    (utc(2, 23, 31), 502, "GET /api/cart/items HTTP/1.1"),
]
WORKER_PANICS = [
    (utc(2, 10, 45), "panic: nil map write in shard 3"),
    (utc(2, 13, 12), "panic: queue index out of range"),
    (utc(2, 16, 40), "panic: nil map write in shard 7"),
    (utc(2, 19, 27), "panic: lost db handle mid-batch"),
    (utc(2, 22, 50), "panic: queue index out of range in retry loop"),
]

# --- 레드 헤링 (윈도우 밖) ---------------------------------------------------
# app: KST 02:1x/02:2x — 오프셋을 무시하고 읽으면 윈도우 안으로 보인다(실제 UTC 는 전날 17시).
APP_HERRINGS = [
    (utc(17, 13, 5, day=13), "db connection pool exhausted (pool=main)"),
    (utc(17, 19, 44, day=13), "session store write failed"),
]
GATEWAY_HERRINGS = [
    (utc(2, 9, 59), 502, "GET /api/cart HTTP/1.1"),  # 시작 1초 전
    (utc(2, 25, 0), 503, "POST /api/checkout HTTP/1.1"),  # 종료 정각(미만이므로 제외)
]
WORKER_HERRINGS = [
    (utc(1, 50, 12), "panic: nil map write in shard 3"),
    (utc(2, 25, 31), "panic: queue index out of range"),
]

APP_FILLER_MSGS = [
    "request served", "cache warmed", "cron tick", "feature flag refreshed",
    "session created", "gc pause 12ms", "config reloaded", "healthcheck ok",
    "retry scheduled", "queue depth nominal", "token rotated", "metrics flushed",
]
GATEWAY_PATHS = [
    "GET / HTTP/1.1", "GET /api/products HTTP/1.1", "GET /static/app.js HTTP/1.1",
    "POST /api/login HTTP/1.1", "GET /api/cart HTTP/1.1", "GET /health HTTP/1.1",
    "GET /api/search?q=shoes HTTP/1.1", "POST /api/cart/items HTTP/1.1",
]
WORKER_FILLER = [
    ("INFO", "job {} done"), ("INFO", "batch {} committed"), ("WARN", "job {} slow: 4.2s"),
    ("INFO", "heartbeat ok seq={}"), ("WARN", "retry {} scheduled"),
]


def rand_dt(start: datetime, end: datetime) -> datetime:
    return start + timedelta(seconds=rng.randrange(int((end - start).total_seconds())))


def build_app() -> list[str]:
    rows: list[tuple[datetime, str, str]] = []
    rows += [(dt, "ERROR", msg) for dt, msg in APP_ERRORS + APP_HERRINGS]
    # 윈도우 안 비수집 레벨(INFO·WARN) — "윈도우 안 = 전부"가 아니게 한다.
    for i in range(10):
        dt = rand_dt(WINDOW_START, WINDOW_END)
        rows.append((dt, "WARN" if i % 3 == 0 else "INFO", rng.choice(APP_FILLER_MSGS)))
    # 넓은 범위 필러 (전날 저녁 ~ 당일 오전, ERROR 없음)
    for _ in range(134):
        dt = rand_dt(utc(16, 0, 0, day=13), utc(5, 0, 0, day=14))
        rows.append((dt, "WARN" if rng.random() < 0.15 else "INFO", rng.choice(APP_FILLER_MSGS)))
    rows.sort(key=lambda t: t[0])
    return [
        json.dumps({"ts": kst_iso(dt), "level": lvl, "msg": msg}, ensure_ascii=False)
        for dt, lvl, msg in rows
    ]


def build_gateway() -> list[str]:
    rows: list[tuple[datetime, int, str]] = list(GATEWAY_5XX) + list(GATEWAY_HERRINGS)
    for _ in range(24):  # 윈도우 안 정상/4xx — 5xx 만 수집됨을 시험
        dt = rand_dt(WINDOW_START, WINDOW_END)
        rows.append((dt, rng.choice([200, 200, 200, 301, 404]), rng.choice(GATEWAY_PATHS)))
    for _ in range(127):
        dt = rand_dt(utc(1, 0, 0), utc(3, 30, 0))
        if WINDOW_START <= dt < WINDOW_END:
            status = rng.choice([200, 200, 404])  # 윈도우 안 필러는 5xx 금지
        else:
            status = rng.choice([200, 200, 200, 200, 301, 404])
        rows.append((dt, status, rng.choice(GATEWAY_PATHS)))
    rows.sort(key=lambda t: t[0])
    lines = []
    for dt, status, req in rows:
        ip = f"10.0.{rng.randrange(1, 8)}.{rng.randrange(2, 250)}"
        size = rng.randrange(120, 9000)
        lines.append(f'{ip} - - [{nginx_time(dt)}] "{req}" {status} {size}')
    return lines


def build_worker() -> list[str]:
    rows: list[tuple[datetime, str, str]] = []
    rows += [(dt, "PANIC", msg) for dt, msg in WORKER_PANICS + WORKER_HERRINGS]
    # 윈도우 안 PANIC 아닌 오류 — "worker 는 PANIC 줄만" 을 시험
    rows.append((utc(2, 12, 3), "ERROR", "job 77 failed: retryable io error"))
    rows.append((utc(2, 18, 21), "ERROR", "job 81 failed: retryable io error"))
    for i in range(111):
        dt = rand_dt(utc(0, 30, 0), utc(4, 0, 0))
        lvl, tpl = WORKER_FILLER[rng.randrange(len(WORKER_FILLER))]
        rows.append((dt, lvl, tpl.format(rng.randrange(100, 999))))
    rows.sort(key=lambda t: t[0])
    return [f"{lvl} {epoch(dt)} {msg}" for dt, lvl, msg in rows]


def expected_rows() -> list[tuple[str, str, str]]:
    rows = []
    rows += [(iso_z(dt), "app", msg) for dt, msg in APP_ERRORS]
    rows += [(iso_z(dt), "gateway", req) for dt, _status, req in GATEWAY_5XX]
    rows += [(iso_z(dt), "worker", msg) for dt, msg in WORKER_PANICS]
    rows.sort(key=lambda t: (t[0], t[1]))
    return rows


def main() -> None:
    task_dir = Path(sys.argv[1]).resolve()
    logs = task_dir / "project" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "app.jsonl").write_text("\n".join(build_app()) + "\n", encoding="utf-8")
    (logs / "gateway.log").write_text("\n".join(build_gateway()) + "\n", encoding="utf-8")
    (logs / "worker.log").write_text("\n".join(build_worker()) + "\n", encoding="utf-8")

    rows = expected_rows()
    assert len(rows) == 18, len(rows)
    for out in (
        task_dir / "solution" / "heldout" / "expected_timeline.csv",
        task_dir / "solution" / "timeline.csv",  # 골든 산출물 (동일 내용)
    ):
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["utc_iso", "source", "detail"])
            writer.writerows(rows)
    print("generated logs + expected_timeline.csv (18 rows)")


if __name__ == "__main__":
    main()
