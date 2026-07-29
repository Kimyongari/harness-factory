"""held-out: API 동작 + README 예제의 실행 가능성·최신성을 함께 본다."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _readme_blocks() -> list[str]:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    return re.findall(r"```(?:python|py)\n(.*?)```", text, re.S)


def test_lookup_by_email():
    from api import get_user

    assert get_user(email="bob@example.com")["name"] == "bob"


def test_lookup_by_id_pass_to_pass():
    from api import get_user

    assert get_user(1)["name"] == "alice"
    assert get_user(user_id=2)["name"] == "bob"


def test_readme_examples_execute():
    blocks = _readme_blocks()
    assert blocks, "README 에 실행 가능한 파이썬 예제가 없다"
    for i, block in enumerate(blocks):
        proc = subprocess.run(
            [sys.executable, "-c", block], cwd=ROOT, capture_output=True, text=True
        )
        assert proc.returncode == 0, f"README 예제 {i + 1} 실행 실패:\n{proc.stderr[-400:]}"


def test_readme_documents_email_lookup():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    api_section = text.split("## API", 1)[-1]
    assert "email" in api_section, "README 의 API 절이 email 조회를 설명하지 않는다"
