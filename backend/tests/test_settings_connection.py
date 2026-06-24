"""连通测试服务测试：验证 check_llm_connection 按配置构建 client 并探测连通性。

mock provider 无需外部连接直接 ok；openai provider 通过 monkeypatch make_llm_client
注入成功/失败 client，验证异常被捕获为 ok=False（不发真实网络请求，测试稳定可复现）。
"""
from quizcraft.services.llm import LLMResponse
from quizcraft.services.settings import connection as conn_mod
from quizcraft.services.settings.connection import ConnectionResult, check_llm_connection


async def test_mock_provider_ok():
    """mock provider 无需外部连接，直接 ok=True。"""
    result = await check_llm_connection(provider="mock", api_key=None, model="gpt-4o", base_url=None)
    assert result.ok is True
    assert result.provider == "mock"
    assert result.model == "gpt-4o"


async def test_openai_success_via_injected_client(monkeypatch):
    """openai provider：注入能 complete 的 client → ok=True。"""

    class _OkClient:
        async def complete(self, messages, **kwargs):
            return LLMResponse(content="pong")

    monkeypatch.setattr(conn_mod, "make_llm_client", lambda settings: _OkClient())

    result = await check_llm_connection(
        provider="openai", api_key="sk-x", model="gpt-4o", base_url=None
    )
    assert result.ok is True
    assert "openai" in result.provider


async def test_openai_failure_captured(monkeypatch):
    """openai provider：注入抛异常的 client → ok=False，message 含错误，不向上抛。"""

    class _BoomClient:
        async def complete(self, messages, **kwargs):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(conn_mod, "make_llm_client", lambda settings: _BoomClient())

    result = await check_llm_connection(
        provider="openai", api_key="sk-x", model="gpt-4o", base_url=None
    )
    assert result.ok is False
    assert "connection refused" in result.message


async def test_openai_missing_api_key_fails(monkeypatch):
    """openai provider 缺 api_key：make_llm_client 抛 ValueError → ok=False。"""

    def _raise(settings):
        raise ValueError("provider=openai 需要配置 api_key")

    monkeypatch.setattr(conn_mod, "make_llm_client", _raise)

    result = await check_llm_connection(
        provider="openai", api_key=None, model="gpt-4o", base_url=None
    )
    assert result.ok is False
    assert "api_key" in result.message


async def test_unknown_provider_fails():
    """未知 provider → ok=False。"""
    result = await check_llm_connection(
        provider="totally-unknown", api_key=None, model="x", base_url=None
    )
    assert result.ok is False


def test_connection_result_is_dataclass():
    """ConnectionResult 是可读 dataclass（路由层直接序列化返回）。"""
    r = ConnectionResult(ok=True, provider="mock", model="gpt-4o", message="ready")
    assert r.ok is True
