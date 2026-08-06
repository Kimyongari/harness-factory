#!/usr/bin/env python3
"""배치 프로세서 — process_spec.md 계약 구현.

핵심: journal.tsv/errors.tsv 가 곧 체크포인트다. 실행 시작 때 두 파일에 이미
기록된 id 를 읽어 건너뛰므로, 어떤 순서로 중단·재개돼도 각 id 는 정확히
한 번만 기록된다. 레코드 1건마다 append+flush 해 중간 중단에도 안전하다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

INBOX = Path("inbox")
OUTPUT = Path("output")
JOURNAL = OUTPUT / "journal.tsv"
ERRORS = OUTPUT / "errors.tsv"
REQUIRED_FIELDS = ("id", "device", "ts", "readings")


def canonical_checksum(obj) -> str:
    """process_spec.md 의 정규화 규칙 그대로."""
    canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def recorded_ids() -> set[str]:
    """체크포인트 복원: 두 산출물 파일에 이미 등장한 id 전부."""
    done: set[str] = set()
    for path in (JOURNAL, ERRORS):
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    done.add(line.split("\t", 1)[0])
    return done


def main() -> None:
    ap = argparse.ArgumentParser(description="inbox 배치 프로세서 (exactly-once)")
    ap.add_argument("--max-id", type=int, default=300, help="rec_001~rec_N 까지만 처리")
    args = ap.parse_args()

    OUTPUT.mkdir(exist_ok=True)
    done = recorded_ids()
    with (
        open(JOURNAL, "a", encoding="utf-8", newline="\n") as journal,
        open(ERRORS, "a", encoding="utf-8", newline="\n") as errors,
    ):
        for path in sorted(INBOX.glob("rec_*.json")):
            rid = path.stem
            if int(rid.split("_")[1]) > args.max_id or rid in done:
                continue
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                errors.write(f"{rid}\tinvalid-json\n")
                errors.flush()
                continue
            missing = [field for field in REQUIRED_FIELDS if field not in obj]
            if missing:
                errors.write(f"{rid}\tmissing-field:{','.join(missing)}\n")
                errors.flush()
                continue
            journal.write(f"{rid}\t{canonical_checksum(obj)}\n")
            journal.flush()


if __name__ == "__main__":
    main()
