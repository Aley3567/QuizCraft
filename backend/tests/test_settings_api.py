"""settings API 测试：GET/POST /api/settings/llm。

验证：
- GET 未配置 → 404
- POST 保存配置 → 返回脱敏视图 + 连通结果，明文 key 不在响应
- POST 后 GET → 读回脱敏配置
- POST 有 api_key 但无 secret → 400（拒绝明文落库）
- POST openai 连通失败仍保存配置（用户可据结果调整），connection.ok=False
"""
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from quizcraft.services.settings import connection as conn_mod


async def test_get_unconfigured_returns_404(client):
    """未配置 LLM 时 GET 返回 404。"""
    resp = await client.get("/api/settings/llm")
    assert resp.status_code == HTTP_404_NOT_FOUND


async def test_post_mock_config_returns_view_and_connection(client, monkeypatch):
    """保存 mock 配置 → 200，脱敏视图 + 连通 ok=True，明文 key 不在响应。"""
    monkeypatch.setenv("QUIZCRAFT_SECRET_KEY", "router-test-secret")

    resp = await client.post(
        "/api/settings/llm",
        json={"provider": "mock", "model": "gpt-4o"},
    )
    assert resp.status_code == HTTP_200_OK, resp.text
    body = resp.json()

    cfg = body["config"]
    assert cfg["provider"] == "mock"
    assert cfg["has_api_key"] is False
    assert cfg["model"] == "gpt-4o"
    # 明文 key 字段绝不出现
    assert "api_key" not in cfg

    conn = body["connection"]
    assert conn["ok"] is True
    assert conn["provider"] == "mock"


async def test_post_then_get_roundtrip(client, monkeypatch):
    """POST 保存后 GET 读回脱敏配置（has_api_key=True 但无明文）。"""
    monkeypatch.setenv("QUIZCRAFT_SECRET_KEY", "router-test-secret")

    resp = await client.post(
        "/api/settings/llm",
        json={
            "provider": "mock",
            "api_key": "sk-should-be-hidden",
            "model": "gpt-4o",
            "base_url": "https://api.example.com/v1",
        },
    )
    assert resp.status_code == HTTP_200_OK
    assert resp.json()["config"]["has_api_key"] is True
    assert "sk-should-be-hidden" not in resp.text  # 明文 key 不出现在整个响应文本

    got = await client.get("/api/settings/llm")
    assert got.status_code == HTTP_200_OK
    cfg = got.json()
    assert cfg["provider"] == "mock"
    assert cfg["has_api_key"] is True
    assert cfg["base_url"] == "https://api.example.com/v1"
    assert "sk-should-be-hidden" not in got.text


async def test_post_without_api_key_preserves_existing_secret(client, monkeypatch):
    """已保存 key 后再次保存 model/base_url 时，可省略 api_key 且保留 has_api_key=True。"""
    monkeypatch.setenv("QUIZCRAFT_SECRET_KEY", "router-test-secret")

    created = await client.post(
        "/api/settings/llm",
        json={
            "provider": "mock",
            "api_key": "sk-hidden",
            "model": "first-model",
        },
    )
    assert created.status_code == HTTP_200_OK
    assert created.json()["config"]["has_api_key"] is True

    updated = await client.post(
        "/api/settings/llm",
        json={
            "provider": "mock",
            "model": "second-model",
            "base_url": "https://api.example.com/v1",
        },
    )
    assert updated.status_code == HTTP_200_OK
    body = updated.json()
    assert body["config"]["model"] == "second-model"
    assert body["config"]["has_api_key"] is True
    assert "sk-hidden" not in updated.text


async def test_post_api_key_without_secret_rejected(client, monkeypatch):
    """有 api_key 但未配置 secret → 400（拒绝明文落库敏感凭证）。"""
    monkeypatch.delenv("QUIZCRAFT_SECRET_KEY", raising=False)

    resp = await client.post(
        "/api/settings/llm",
        json={"provider": "openai", "api_key": "sk-leak", "model": "gpt-4o"},
    )
    assert resp.status_code == 400
    assert "secret" in resp.json()["detail"].lower()


async def test_post_openai_connection_failure_still_saved(client, monkeypatch):
    """openai 连通失败仍保存配置，connection.ok=False 且 message 含错误。

    monkeypatch make_llm_client 注入抛错 client——保存不依赖连通，用户可据结果调整。
    """
    monkeypatch.setenv("QUIZCRAFT_SECRET_KEY", "router-test-secret")

    class _BoomClient:
        async def complete(self, messages, **kwargs):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(conn_mod, "make_llm_client", lambda settings: _BoomClient())

    resp = await client.post(
        "/api/settings/llm",
        json={"provider": "openai", "api_key": "sk-x", "model": "gpt-4o"},
    )
    assert resp.status_code == HTTP_200_OK, resp.text
    body = resp.json()
    assert body["config"]["has_api_key"] is True  # 配置仍保存
    assert body["connection"]["ok"] is False
    assert "connection refused" in body["connection"]["message"]
