"""held-out: 정상 읽기 + 경로 탈출 차단. 구현 방식(예외/None)에 중립적으로 채점한다.

미끼 파일은 **채점 시점에 이 테스트가 만들고 곧바로 지운다.** 시작 상태에 두면 두 가지가 깨진다:
  1) 에이전트가 그 파일을 읽고 무엇을 시험하는지 알아챈다(오염)
  2) 에이전트가 그 파일을 지우면 취약한 구현도 "탈출한 내용 없음" 으로 통과한다(위조)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DECOY = "outside-notes-marker-4471"
DECOY_FILE = ROOT / "secret.md"
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
    try:
        from notes import read_note

        return read_note(name)
    except Exception:  # 예외로 막는 것도 정답
        return None


def test_reads_valid_note():
    from notes import read_note, save_note

    save_note("memo", "본문입니다")
    assert "본문입니다" in read_note("memo")
    assert "hello" in read_note("hello")


def test_blocks_traversal():
    """notes/ 밖의 파일을 만들어 두고, 탈출 시도가 그 내용을 반환하는지 본다."""
    existed = DECOY_FILE.exists()
    original = DECOY_FILE.read_text(encoding="utf-8") if existed else None
    DECOY_FILE.write_text(f"{DECOY}\n", encoding="utf-8")
    try:
        leaked = [name for name in ATTACKS if DECOY in (_read(name) or "")]
        assert not leaked, f"경로 탈출로 notes/ 밖 파일이 읽혔다: {leaked}"
    finally:
        if original is None:
            DECOY_FILE.unlink(missing_ok=True)
        else:
            DECOY_FILE.write_text(original, encoding="utf-8")


def test_save_note_still_works():
    from notes import list_notes, save_note

    save_note("regress", "x")
    assert "regress" in list_notes()
