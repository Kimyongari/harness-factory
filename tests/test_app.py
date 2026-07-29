"""FastAPI 계층 테스트 — 기본 언어와 배포 배선의 드리프트를 막는다.

`test_engine.py` 가 생성기(engine)를, `test_eval.py` 가 평가 스위트를 본다면
여기서는 **웹 앱이 방문자에게 무엇을 먼저 보여주는가** 와 **프록시 배선이 맞는가** 를 본다.
둘 다 한 곳만 고치면 조용히 어긋나는 종류라 테스트로 묶어둔다.
"""

import re
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from harness_maker.app import DEFAULT_LANG, LANGS, app

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = REPO_ROOT / "src" / "harness_maker" / "static" / "index.html"
NGINX_CONF = REPO_ROOT / "deploy" / "nginx.conf"
DEPLOY_YML = REPO_ROOT / ".github" / "workflows" / "deploy.yml"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ------------------------------------------------------------------ 기본 언어
def test_default_lang_is_english():
    """방문자가 언어를 고르지 않았을 때의 기본값."""
    assert DEFAULT_LANG == "en"
    assert DEFAULT_LANG in LANGS


def test_survey_defaults_to_english(client):
    """`/api/survey` 를 lang 없이 호출하면 영어 설문이 온다."""
    data = client.get("/api/survey").json()
    assert data["lang"] == "en"


def test_survey_honors_explicit_lang(client):
    """명시하면 그 언어로 온다 — 기본값 변경이 전환 기능을 깨뜨리지 않았는지."""
    for lang in LANGS:
        assert client.get(f"/api/survey?lang={lang}").json()["lang"] == lang


def test_unknown_lang_falls_back_to_default(client):
    assert client.get("/api/survey?lang=fr").json()["lang"] == DEFAULT_LANG


def test_frontend_initial_lang_matches_backend():
    """프런트엔드 초기 언어가 백엔드 기본값과 같아야 한다.

    한쪽만 바꾸면 첫 화면은 A 언어로 그려지고 설문 데이터는 B 언어로 오는 상태가 된다 —
    화면은 그럴듯하게 렌더링되므로 눈으로는 잘 안 잡힌다.
    """
    html = INDEX_HTML.read_text(encoding="utf-8")
    initial = re.search(r"let LANG = '(\w+)'", html)
    boot = re.search(r"load\('(\w+)'\);", html)
    root = re.search(r'<html lang="(\w+)"', html)
    assert initial and boot and root, "index.html 에서 언어 초기화 지점을 찾지 못했다"
    assert initial.group(1) == DEFAULT_LANG, f"let LANG = {initial.group(1)!r}"
    assert boot.group(1) == DEFAULT_LANG, f"load({boot.group(1)!r})"
    assert root.group(1) == DEFAULT_LANG, f'<html lang="{root.group(1)}">'


def test_language_toggle_offers_every_supported_lang():
    html = INDEX_HTML.read_text(encoding="utf-8")
    offered = set(re.findall(r'data-lang="(\w+)"', html))
    assert offered == set(LANGS), f"토글 선택지={offered} 지원 언어={set(LANGS)}"


# ------------------------------------------------------------- 프록시 배선
REMOTE_DEPLOY = REPO_ROOT / "deploy" / "remote-deploy.sh"


def test_nginx_upstream_matches_published_app_port():
    """프록시가 넘기는 포트와 배포가 앱을 공개하는 호스트 포트가 같아야 한다.

    다르면 사이트가 502 를 뱉는다. 두 파일이 떨어져 있어 한쪽만 고치기 쉬운 조합이다.
    """
    conf = NGINX_CONF.read_text(encoding="utf-8")
    upstream = re.search(r"proxy_pass http://127\.0\.0\.1:(\d+);", conf)
    assert upstream, "nginx.conf 의 proxy_pass 에서 호스트 포트를 찾지 못했다"

    script = REMOTE_DEPLOY.read_text(encoding="utf-8")
    port = re.search(r"^PORT=(\d+)", script, re.M)
    assert port, "remote-deploy.sh 에서 PORT 를 찾지 못했다"
    assert upstream.group(1) == port.group(1), (
        f"프록시 업스트림 포트={upstream.group(1)} 배포 공개 포트={port.group(1)}"
    )


def test_proxy_uses_host_network():
    """프록시는 호스트 네트워크로 떠야 127.0.0.1:<앱포트> 로 앱에 닿는다.

    브리지 네트워크로 띄우면 127.0.0.1 이 컨테이너 자신을 가리켜 502 가 된다.
    """
    script = REMOTE_DEPLOY.read_text(encoding="utf-8")
    proxy_run = re.search(r'docker run -d --name "\$\{PROXY\}".*?nginx:[\w.-]+', script, re.S)
    assert proxy_run, "remote-deploy.sh 에서 프록시 기동 명령을 찾지 못했다"
    assert "--network host" in proxy_run.group(), "프록시가 --network host 로 뜨지 않는다"


def test_proxy_body_limit_is_above_app_limit():
    """프록시 한도가 앱 한도보다 작으면 앱의 413 메시지 대신 nginx 기본 페이지가 나간다."""
    from harness_maker.app import MAX_BODY_BYTES

    conf = NGINX_CONF.read_text(encoding="utf-8")
    limit = re.search(r"client_max_body_size (\d+)m", conf)
    assert limit, "client_max_body_size 설정이 없다"
    assert int(limit.group(1)) * 1024 * 1024 > MAX_BODY_BYTES


# ------------------------------------------------------------- 배포 로그 계약
def test_deploy_script_records_status_and_history():
    """배포 스크립트는 성공/실패를 파일로 남겨야 한다 — CI 가 그것으로 판정한다.

    SSH 채널이 끊겨도 결과를 알 수 있게 하는 장치이므로, 종료 트랩으로 걸려 있어야 한다.
    """
    script = REMOTE_DEPLOY.read_text(encoding="utf-8")
    assert "trap summarize EXIT" in script, "종료 트랩이 없다 — 실패가 기록되지 않는다"
    for artifact in ("history.log", "last-status"):
        assert artifact in script, f"{artifact} 를 남기지 않는다"
    assert re.search(r"STEP=\w+", script), "실패 지점을 남기는 STEP 마커가 없다"


def test_workflow_launches_detached_and_polls_status():
    """CI 는 배포를 분리 실행하고 결과 파일을 폴링해야 한다.

    SSH 채널 안에서 배포를 돌리면 채널이 끊기는 순간 배포가 중단된다(실제로 발생).
    """
    deploy = DEPLOY_YML.read_text(encoding="utf-8")
    assert "setsid nohup bash deploy/remote-deploy.sh" in deploy, "분리 실행이 아니다"
    assert "last-status" in deploy, "결과 파일을 폴링하지 않는다"
    assert "rm -f deploy-logs/last-status" in deploy, (
        "이전 실행의 결과 파일을 지우지 않으면 곧바로 낡은 성공을 읽는다"
    )


def test_ci_workflow_still_parses():
    """워크플로 YAML 이 깨지면 배포가 아예 돌지 않는다 — 문법만이라도 지킨다."""
    for path in (DEPLOY_YML, REPO_ROOT / ".github" / "workflows" / "ci.yml"):
        assert yaml.safe_load(path.read_text(encoding="utf-8"))
