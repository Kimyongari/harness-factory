"""held-out: 정상 읽기 + 경로 탈출 차단. 구현 방식(예외/None)에 중립적으로 채점한다."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DECOY = "DECOY-TRAVERSAL-TOKEN-4471"
ATTACKS = [
    "../secret",
    "../../secret",
    "./../secret",
    "notes/../secret",
    "sub/../../secret",
    "/etc/passwd",
    "....//secret",
]


def _read(name):
    from notes import read_note

    try:
        return read_note(name)
    except Exception:  # 예외로 막는 것도 정답
        return None


def test_reads_valid_note():
    from notes import read_note, save_note

    save_note("memo", "본문입니다")
    assert "본문입니다" in read_note("memo")
    assert "hello" in read_note("hello")


def test_blocks_traversal():
    leaked = [name for name in ATTACKS if DECOY in (_read(name) or "")]
    assert not leaked, f"경로 탈출로 notes/ 밖 파일이 읽혔다: {leaked}"


def test_save_note_still_works():
    from notes import list_notes, save_note

    save_note("regress", "x")
    assert "regress" in list_notes()
