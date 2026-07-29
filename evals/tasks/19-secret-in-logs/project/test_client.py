import client


def test_request_builds_url(monkeypatch):
    seen = {}

    def fake_send(method, url, headers, body):
        seen.update(method=method, url=url, headers=headers)
        return {"ok": True}

    monkeypatch.setattr(client, "_send", fake_send)
    assert client.request("GET", "/ping") == {"ok": True}
    assert seen["url"].endswith("/ping")
