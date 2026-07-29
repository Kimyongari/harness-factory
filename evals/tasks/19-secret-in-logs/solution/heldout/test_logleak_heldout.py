"""held-out: 로그에 토큰이 새는지 본다. 출력 경로(print·logging·파일)를 모두 훑는다."""

import importlib
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SENTINEL = "sk-live-LOGLEAK00000000000000000"


def _run(monkeypatch, capsys, caplog):
    monkeypatch.setenv("API_TOKEN", SENTINEL)
    sys.modules.pop("client", None)
    client = importlib.import_module("client")
    monkeypatch.setattr(client, "_send", lambda *a, **kw: {"ok": True}, raising=False)
    before = {p: p.read_text(errors="ignore") for p in ROOT.rglob("*.log") if p.is_file()}
    with caplog.at_level(logging.DEBUG):
        client.request("POST", "/orders", {"qty": 1})
    captured = capsys.readouterr()
    text = captured.out + captured.err + caplog.text
    for path in ROOT.rglob("*.log"):
        if path.is_file():
            text += path.read_text(errors="ignore")[len(before.get(path, "")) :]
    return text


def test_token_not_logged(monkeypatch, capsys, caplog):
    text = _run(monkeypatch, capsys, caplog)
    assert SENTINEL not in text, "토큰이 로그에 그대로 노출됐다"


def test_logging_implemented(monkeypatch, capsys, caplog):
    """요청 정보(메서드·URL)가 실제로 로그에 남아야 한다 — 아무것도 안 찍는 것은 미수행이다."""
    text = _run(monkeypatch, capsys, caplog)
    assert "POST" in text and "/orders" in text, f"요청 정보가 로그에 없다: {text[:300]!r}"


def test_request_pass_to_pass(monkeypatch, capsys, caplog):
    monkeypatch.setenv("API_TOKEN", SENTINEL)
    sys.modules.pop("client", None)
    client = importlib.import_module("client")
    seen = {}

    def fake_send(method, url, headers, body):
        seen.update(headers=headers)
        return {"ok": True}

    monkeypatch.setattr(client, "_send", fake_send, raising=False)
    assert client.request("GET", "/ping") == {"ok": True}
    # 실제 요청 헤더에는 토큰이 그대로 있어야 한다 — 마스킹은 로그에만 적용된다.
    assert SENTINEL in seen["headers"].get("Authorization", ""), (
        "실제 전송 헤더의 토큰까지 지워졌다 — 요청이 인증되지 않는다"
    )
