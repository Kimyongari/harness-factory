"""파일 기반 노트 저장소."""

from __future__ import annotations

from pathlib import Path

NOTES_DIR = Path(__file__).parent / "notes"


def save_note(name: str, body: str) -> None:
    NOTES_DIR.mkdir(exist_ok=True)
    (NOTES_DIR / f"{name}.md").write_text(body, encoding="utf-8")


def list_notes() -> list[str]:
    return sorted(p.stem for p in NOTES_DIR.glob("*.md"))
