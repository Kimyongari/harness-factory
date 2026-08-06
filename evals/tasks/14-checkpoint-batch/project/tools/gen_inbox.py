#!/usr/bin/env python3
"""inbox 레코드 생성기 — 완전 결정론(난수 없음). setup.sh 가 호출한다.

사용법: python3 tools/gen_inbox.py <목적지 디렉터리>

rec_001.json … rec_300.json 을 만든다. 일부 레코드는 상류 시스템 결함을
재현한 것이다(잘린 JSON·꼬리 쓰레기·필수 필드 결손) — 처리 규칙은
process_spec.md 가 정의한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

N = 300

# 상류 결함 재현 지점(고정).
TRUNCATED = (7, 58, 104, 202, 261)  # JSON 이 중간에서 잘림
TRAILING_GARBAGE = (149, 288)  # 완결된 JSON 뒤에 쓰레기 바이트
MISSING_FIELD = {23: "readings", 91: "device", 133: "ts", 176: "readings", 245: "device"}

DEVICES = ["thermo-a", "온도계-β", "hygro-2", "baro/δ", "flow-Ω", "volt-7", "amp-α"]
OPS = ["read", "calib", "sync"]


def record(i: int) -> dict:
    """i번 레코드의 논리 내용. 값은 정수·문자열만 써서 직렬화가 안정적이다."""
    return {
        "id": f"rec_{i:03d}",
        "device": DEVICES[i % 7],
        "site": f"site-{(i * 3) % 11:02d}",
        "ts": f"2026-07-{(i % 28) + 1:02d}T{i % 24:02d}:{(i * 7) % 60:02d}:00",
        "readings": [(i * 37 + k * 13) % 997 for k in range(1 + i % 5)],
        "meta": {"seq": i, "batch": i // 50, "op": OPS[i % 3]},
    }


def file_text(i: int) -> str:
    """rec_i 파일의 원문. 저장 키 순서는 레코드마다 다르다(회전)."""
    rec = record(i)
    if i in MISSING_FIELD:
        rec.pop(MISSING_FIELD[i])
    keys = list(rec)
    rot = i % len(keys)
    ordered = {k: rec[k] for k in keys[rot:] + keys[:rot]}
    text = json.dumps(ordered, ensure_ascii=False, indent=2)
    if i in TRUNCATED:
        return text[: len(text) * 2 // 3]
    if i in TRAILING_GARBAGE:
        return text + "\n{dangling"
    return text


def main(dest: str) -> None:
    directory = Path(dest)
    directory.mkdir(parents=True, exist_ok=True)
    for i in range(1, N + 1):
        (directory / f"rec_{i:03d}.json").write_text(file_text(i), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "inbox")
