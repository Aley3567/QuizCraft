"""settings store 测试：LLM 配置的加密保存 / 读取 round-trip。

用 session fixture（内存 SQLite），验证：
- save → load 还原（api_key 解密、CJK model 名）
- secret 不匹配 load 失败
- 无配置 load 返回 None
- 无 api_key 的配置（mock provider）不需 secret 也能存
- 有 api_key 但 secret 空 → 拒绝（不 fallback 明文落库）
- 同 key 二次保存覆盖更新
"""
import pytest

from quizcraft.services.settings.store import (
    LLMConfig,
    load_llm_config,
    load_llm_config_view,
    save_llm_config,
)

SECRET = "test-quizcraft-secret"


async def test_save_and_load_roundtrip(session):
    """保存后读取还原全部字段，api_key 解密回明文。"""
    config = LLMConfig(
        provider="openai",
        api_key="sk-proj-secret-key",
        model="gpt-4o中文测试",
        base_url="https://api.example.com/v1",
    )
    await save_llm_config(session, config, SECRET)

    loaded = await load_llm_config(session, SECRET)
    assert loaded is not None
    assert loaded.provider == "openai"
    assert loaded.api_key == "sk-proj-secret-key"
    assert loaded.model == "gpt-4o中文测试"
    assert loaded.base_url == "https://api.example.com/v1"


async def test_load_returns_none_when_unconfigured(session):
    """未配置任何 LLM 时 load 返回 None。"""
    assert await load_llm_config(session, SECRET) is None


async def test_load_wrong_secret_raises(session):
    """save 用 secret1，load 用 secret2 → 解密失败抛 ValueError。"""
    await save_llm_config(
        session, LLMConfig(provider="openai", api_key="sk-real", model="gpt-4o"), SECRET
    )
    with pytest.raises(ValueError, match="secret"):
        await load_llm_config(session, "wrong-secret")


async def test_save_mock_config_without_secret_ok(session):
    """mock provider 无 api_key，secret 为空也能保存（不需加密）。"""
    config = LLMConfig(provider="mock", api_key=None, model="gpt-4o", base_url=None)
    await save_llm_config(session, config, secret="")

    loaded = await load_llm_config(session, secret="")
    assert loaded is not None
    assert loaded.provider == "mock"
    assert loaded.api_key is None


async def test_save_api_key_without_secret_rejected(session):
    """有 api_key 但 secret 空 → 拒绝保存（不 fallback 明文落库敏感凭证）。"""
    config = LLMConfig(provider="openai", api_key="sk-leak", model="gpt-4o")
    with pytest.raises(ValueError, match="secret"):
        await save_llm_config(session, config, secret="")


async def test_save_overwrites_existing(session):
    """同 key 二次保存覆盖更新，不产生重复行。"""
    await save_llm_config(
        session, LLMConfig(provider="openai", api_key="sk-old", model="gpt-4o"), SECRET
    )
    await save_llm_config(
        session, LLMConfig(provider="openai", api_key="sk-new", model="gpt-4o-mini"), SECRET
    )

    loaded = await load_llm_config(session, SECRET)
    assert loaded.api_key == "sk-new"
    assert loaded.model == "gpt-4o-mini"

    # 单行 KV：settings 表只有一条 llm_config 记录
    from sqlalchemy import select

    from quizcraft.models.setting import Setting

    rows = (await session.execute(select(Setting).where(Setting.key == "llm_config"))).all()
    assert len(rows) == 1


async def test_api_key_none_persists_and_loads_none(session):
    """api_key=None 的配置 round-trip 保持 None。"""
    config = LLMConfig(provider="openai", api_key=None, model="gpt-4o", base_url=None)
    await save_llm_config(session, config, SECRET)

    loaded = await load_llm_config(session, SECRET)
    assert loaded is not None
    assert loaded.api_key is None


# ---------- 脱敏视图（GET /api/settings/llm 用，不暴露明文 key）----------


async def test_view_unconfigured_returns_none(session):
    """未配置时 view 返回 None。"""
    assert await load_llm_config_view(session) is None


async def test_view_hides_api_key_but_flags_configured(session):
    """view 暴露 provider/model/base_url 明文，api_key 仅以 has_api_key 布尔暴露。"""
    await save_llm_config(
        session,
        LLMConfig(provider="openai", api_key="sk-super-secret", model="gpt-4o"),
        SECRET,
    )

    view = await load_llm_config_view(session)
    assert view is not None
    assert view.provider == "openai"
    assert view.has_api_key is True
    assert view.model == "gpt-4o"
    # 视图对象不持有明文 key 字段，杜绝序列化泄露
    assert not hasattr(view, "api_key")


async def test_view_no_api_key_flagged_false(session):
    """无 api_key 的配置（mock provider）has_api_key=False。"""
    await save_llm_config(
        session, LLMConfig(provider="mock", api_key=None, model="gpt-4o"), SECRET
    )

    view = await load_llm_config_view(session)
    assert view is not None
    assert view.has_api_key is False
