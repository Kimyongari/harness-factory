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
def test_nginx_upstream_matches_deployed_container_name():
    """프록시가 가리키는 이름과 배포가 만드는 컨테이너 이름이 같아야 한다.

    다르면 사이트가 502 를 뱉는다. 두 파일이 떨어져 있어 한쪽만 고치기 쉬운 조합이다.
    """
    conf = NGINX_CONF.read_text(encoding="utf-8")
    upstream = re.search(r'set \$upstream "http://([\w.-]+):(\d+)"', conf)
    assert upstream, "nginx.conf 에서 업스트림 정의를 찾지 못했다"
    name, port = upstream.group(1), upstream.group(2)

    deploy = DEPLOY_YML.read_text(encoding="utf-8")
    app_name = re.search(r"^\s*APP=([\w.-]+)", deploy, re.M)
    assert app_name, "deploy.yml 에서 APP 컨테이너 이름을 찾지 못했다"
    assert name == app_name.group(1), f"프록시 업스트림={name} 배포 컨테이너={app_name.group(1)}"
    assert port == "8000", f"컨테이너 내부 포트는 8000 이어야 한다(현재 {port})"


def test_nginx_resolves_upstream_dynamically():
    """proxy_pass 에 이름을 직접 쓰면 nginx 가 기동 시점 IP 를 캐시해 컨테이너 교체 후 502 가 된다.

    변수 + resolver 조합이어야 배포 때 앱 컨테이너가 바뀌어도 따라간다.
    """
    conf = NGINX_CONF.read_text(encoding="utf-8")
    assert "resolver 127.0.0.11" in conf, "도커 임베디드 DNS resolver 설정이 없다"
    assert re.search(r"proxy_pass \$\w+;", conf), "proxy_pass 가 변수를 쓰지 않는다"


def test_proxy_body_limit_is_above_app_limit():
    """프록시 한도가 앱 한도보다 작으면 앱의 413 메시지 대신 nginx 기본 페이지가 나간다."""
    from harness_maker.app import MAX_BODY_BYTES

    conf = NGINX_CONF.read_text(encoding="utf-8")
    limit = re.search(r"client_max_body_size (\d+)m", conf)
    assert limit, "client_max_body_size 설정이 없다"
    assert int(limit.group(1)) * 1024 * 1024 > MAX_BODY_BYTES


def test_deploy_attaches_app_and_proxy_to_same_network():
    """같은 사용자 정의 네트워크에 있어야 컨테이너 이름으로 서로를 찾을 수 있다."""
    deploy = DEPLOY_YML.read_text(encoding="utf-8")
    assert re.search(r"docker network create \"\$\{NET\}\"", deploy), "네트워크 생성 단계가 없다"
    runs = re.findall(r"docker run -d --name \"\$\{(\w+)\}\"[^\n]*(?:\\\n[^\n]*)*", deploy)
    assert "APP" in runs and "PROXY" in runs, f"컨테이너 기동 지점을 찾지 못했다: {runs}"
    for block in re.findall(
        r"docker run -d --name \"\$\{(?:APP|PROXY)\}\".*?(?=\n\n|\n            #)", deploy, re.S
    ):
        assert '--network "${NET}"' in block, f"네트워크 미지정 기동:\n{block}"


def test_ci_workflow_still_parses():
    """워크플로 YAML 이 깨지면 배포가 아예 돌지 않는다 — 문법만이라도 지킨다."""
    for path in (DEPLOY_YML, REPO_ROOT / ".github" / "workflows" / "ci.yml"):
        assert yaml.safe_load(path.read_text(encoding="utf-8"))
