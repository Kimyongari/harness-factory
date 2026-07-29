"""tests/ 공용 픽스처."""

import os

import pytest


@pytest.fixture(autouse=True)
def _no_ambient_git_env(monkeypatch):
    """스위트를 git 훅 아래에서도 헤르메틱하게 만든다.

    pre-push 훅이 pytest 를 돌리면 git 이 GIT_DIR·GIT_INDEX_FILE 을 레포로 향하게
    설정한 채 상속시킨다. 테스트가 띄우는 서브프로세스(git·하네스 스크립트)가 이를
    물려받으면 임시 디렉터리가 아니라 진짜 레포를 읽고 쓴다.
    """
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(key, raising=False)
