from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from app.main import app

AUTH = {"Authorization": "Bearer local-dev-key"}


def _use_temp_database(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "app.db.settings",
        SimpleNamespace(database_path=str(tmp_path / "requests.db")),
    )


def _mock_upstream(handler):
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1:8001",
        timeout=30.0,
    )


def test_root(monkeypatch, tmp_path):
    _use_temp_database(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "GLM LocalServe"


def test_health_reports_upstream(monkeypatch, tmp_path):
    _use_temp_database(monkeypatch, tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok"})

    with TestClient(app) as client:
        client.app.state.upstream = _mock_upstream(handler)
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["upstream"] == "ok"


def test_auth_is_required(monkeypatch, tmp_path):
    _use_temp_database(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hello"}]},
        )
    assert response.status_code == 401


def test_chat_completion_is_proxied_and_logged(monkeypatch, tmp_path):
    _use_temp_database(monkeypatch, tmp_path)
    captured_body = b""
    upstream_payload = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "zai-org/GLM-4-9B-0414",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "hello back"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_body = request.content
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, json=upstream_payload)

    with TestClient(app) as client:
        client.app.state.upstream = _mock_upstream(handler)
        response = client.post(
            "/v1/chat/completions",
            headers=AUTH,
            json={"messages": [{"role": "user", "content": "hello"}]},
        )
        stats = client.get("/stats", headers=AUTH)

    assert b"zai-org/GLM-4-9B-0414" in captured_body
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "hello back"
    assert stats.status_code == 200
    assert stats.json()["requests"][0]["completion_tokens"] == 2


def test_models_is_proxied(monkeypatch, tmp_path):
    _use_temp_database(monkeypatch, tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        return httpx.Response(
            200,
            json={"object": "list", "data": [{"id": "zai-org/GLM-4-9B-0414"}]},
        )

    with TestClient(app) as client:
        client.app.state.upstream = _mock_upstream(handler)
        response = client.get("/v1/models", headers=AUTH)

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "zai-org/GLM-4-9B-0414"
