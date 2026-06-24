"""LLM 连通测试：按配置构建临时 client 发一次 ping，捕获结果。

用于 Settings 页"测试连接"——配置后立即验证 provider/key/model 可连通，
不让用户保存了一份坏配置后到出题时才发现。真实 openai 调用需 yufeng 的 key，
测试通过 monkeypatch make_llm_client 注入成功/失败 client，不发真实网络请求。
"""
from __future__ import annotations

from dataclasses import dataclass

from quizcraft.config import Settings
from quizcraft.services.llm import Message, make_llm_client


@dataclass
class ConnectionResult:
    """连通测试结果，路由层直接序列化返回给前端。"""

    ok: bool
    provider: str
    model: str | None
    message: str


async def check_llm_connection(
    *, provider: str, api_key: str | None, model: str | None, base_url: str | None
) -> ConnectionResult:
    """按给定配置构建 client 并发一次 ping，返回连通结果。

    任何异常（构造失败 / 调用失败）都被捕获为 ok=False——配置坏时不向上抛，
    让用户在 Settings 页直接看到错误信息而非 500。
    """
    settings = Settings(
        llm_provider=provider,
        llm_api_key=api_key,
        llm_model=model or "gpt-4o",
        llm_base_url=base_url,
    )

    try:
        client = make_llm_client(settings)
        await client.complete([Message(role="user", content="ping")])
    except Exception as exc:  # noqa: BLE001 连通测试需捕获构造与调用的一切异常向用户报告，不 500
        return ConnectionResult(ok=False, provider=provider, model=model, message=str(exc))

    if provider == "mock":
        message = "mock provider 已就绪，无需外部连接"
    else:
        message = "连接成功"
    return ConnectionResult(ok=True, provider=provider, model=model, message=message)
