"""파일 기반 노트 저장소."""

from __future__ import annotations

from pathlib import Path

NOTES_DIR = Path(__file__).parent / "notes"


def _note_path(name: str) -> Path:
    """이름을 notes/ 안의 경로로 해석한다. 탈출 시도는 ValueError."""
    if not name or "/" in name or "\\" in name or name in (".", ".."):
        raise ValueError(f"허용되지 않는 노트 이름: {name!r}")
    path = (NOTES_DIR / f"{name}.md").resolve()
    if path.parent != NOTES_DIR.resolve():
        raise ValueError(f"notes/ 밖을 가리키는 이름: {name!r}")
    return path


def save_note(name: str, body: str) -> None:
    NOTES_DIR.mkdir(exist_ok=True)
    _note_path(name).write_text(body, encoding="utf-8")


def read_note(name: str) -> str:
    return _note_path(name).read_text(encoding="utf-8")


def list_notes() -> list[str]:
    return sorted(p.stem for p in NOTES_DIR.glob("*.md"))
