#!/usr/bin/env python3
"""RESTRUCTURE.md 규칙대로 assets/ 를 재구성한다. 멱등 — 재실행 시 아무것도 하지 않는다.

멱등성의 핵심: assets/ **바로 아래**(재귀 아님)만 대상으로 삼는다. 1회차에 media/·docs/·
unsorted/ 로 들어간 파일은 2회차의 대상 집합에 아예 나타나지 않으므로 재분류가 없다.
"""

import fnmatch
import re
import shutil
from datetime import datetime
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
IMG = re.compile(r"^img_(\d{8})_(.+)\.png$")
DOC = re.compile(r"^doc_(\d{8})_(.+)\.md$")


def parse_date(digits: str) -> datetime | None:
    try:
        return datetime.strptime(digits, "%Y%m%d")
    except ValueError:
        return None


def classify(name: str):
    """(종류, 날짜문자열, slug) — 규칙 1·2·4 판정. 해당 없으면 ('other', ...)"""
    for kind, pat in (("img", IMG), ("doc", DOC)):
        m = pat.match(name)
        if m and parse_date(m.group(1)):
            return kind, m.group(1), m.group(2)
    if fnmatch.fnmatch(name, "tmp_*.tmp"):
        return "tmp", "", ""
    return "other", "", ""


def main() -> None:
    if not ASSETS.is_dir():
        return
    groups: dict[tuple[Path, str, str], list[tuple[str, Path]]] = {}
    for path in sorted(p for p in ASSETS.iterdir() if p.is_file()):
        kind, date, slug = classify(path.name)
        if kind == "img":
            groups.setdefault((ASSETS / "media" / date[:4] / date[4:6], slug, ".png"), []).append(
                (date, path)
            )
        elif kind == "doc":
            groups.setdefault((ASSETS / "docs" / date[:4], slug, ".md"), []).append((date, path))
        elif kind == "tmp":
            path.unlink()
        else:
            dest = ASSETS / "unsorted" / path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(dest))

    for (base, slug, ext), items in groups.items():
        items.sort()  # 날짜 오름차순 (같은 날짜는 파일명순 — 픽스처에는 없음)
        base.mkdir(parents=True, exist_ok=True)
        for i, (_, path) in enumerate(items):
            name = f"{slug}{ext}" if i == 0 else f"{slug}-{i + 1}{ext}"
            shutil.move(str(path), str(base / name))


if __name__ == "__main__":
    main()
