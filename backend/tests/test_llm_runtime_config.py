"""运行时 LLM 配置测试（子系统1 后端增量）：get_llm_client 优先读 DB 配置，回退 env。

子系统1 闭环的最后一块：之前 Settings 页保存的 DB 配置只能存 / 读脱敏视图，运行时出题/答题
仍走 env（get_llm_client 直接 make_llm_client(get_settings())）。本增量让 get_llm_client
优先读 DB settings，未配置或读取失败回退 env——用户配置后无需重启即生效。

覆盖：
- resolve_llm_settings 纯解析逻辑：DB 优先 / DB 缺失回退 env / 解密失败回退 env / DB model 缺失用 env model
- get_llm_client 依赖：DB 配置 → 用 DB 构建 client；未配置 → 用 env 构建
- 路由集成：真实 async-gen get_llm_client 经 Depends 在 generate-quiz 路由解析，读 DB 配置生效
"""
from quizcraft.config import Settings
from quizcraft.dependencies import get_llm_client, resolve_llm_settings
from quizcraft.models.document import Document, DocumentStatus, Section
from quizcraft.services.llm import MockLLMClient
from quizcraft.services.settings import LLMConfig, save_llm_config

SECRET = "runtime-config-secret"


# ---------- resolve_llm_settings：纯解析逻辑（DB 优先 / env 回退）----------


async def test_resolve_uses_db_config_when_present(session):
    """DB 已存配置 → 解析出 DB 的 provider/api_key/model/base_url。"""
    await save_llm_config(
        session,
        LLMConfig(
            provider="openai",
            api_key="sk-db-runtime",
            model="db-special",
            base_url="https://db.example.com/v1",
        ),
        SECRET,
    )

    resolved = await resolve_llm_settings(session, Settings(secret_key=SECRET))

    assert resolved.llm_provider == "openai"
    assert resolved.llm_api_key == "sk-db-runtime"
    assert resolved.llm_model == "db-special"
    assert resolved.llm_base_url == "https://db.example.com/v1"


async def test_resolve_falls_back_to_env_when_unconfigured(session):
    """DB 无配置 → 返回 env settings 不变。"""
    env = Settings(llm_provider="mock", llm_model="gpt-4o")

    resolved = await resolve_llm_settings(session, env)

    assert resolved.llm_provider == "mock"
    assert resolved.llm_model == "gpt-4o"


async def test_resolve_falls_back_to_env_on_decrypt_failure(session):
    """secret 不匹配导致解密失败 → 回退 env（不阻断，保守降级）。"""
    await save_llm_config(
        session,
        LLMConfig(provider="openai", api_key="sk-real", model="gpt-4o"),
        SECRET,
    )

    # 用错误 secret 解析 → load_llm_config 抛 ValueError → 回退 env
    resolved = await resolve_llm_settings(session, Settings(secret_key="wrong-secret"))

    assert resolved.llm_provider == "mock"  # env 默认 mock，未用 DB openai


async def test_resolve_uses_env_model_when_db_model_missing(session):
    """DB 配置 model 为空 → 用 env 的 model 兜底。"""
    await save_llm_config(
        session,
        LLMConfig(provider="mock", api_key=None, model=None, base_url=None),
        SECRET,
    )

    resolved = await resolve_llm_settings(
        session, Settings(secret_key=SECRET, llm_model="gpt-4o")
    )

    assert resolved.llm_provider == "mock"
    assert resolved.llm_model == "gpt-4o"  # env 兜底，非 None


# ---------- get_llm_client 依赖：DB 配置 → DB client / 未配置 → env client ----------


def _record_make_llm_client(monkeypatch):
    """替换 dependencies.make_llm_client 为记录器：捕获传入 settings，返回 MockLLMClient。"""
    import quizcraft.dependencies as deps

    recorded: list[Settings] = []

    def fake_make(settings):
        recorded.append(settings)
        return MockLLMClient()

    monkeypatch.setattr(deps, "make_llm_client", fake_make)
    return recorded


async def test_get_llm_client_reads_db_config(session, monkeypatch):
    """DB 有配置 → get_llm_client 用 DB 配置构建 client（捕获到 DB 的 model）。"""
    await save_llm_config(
        session,
        LLMConfig(provider="mock", api_key=None, model="db-special"),
        SECRET,
    )
    monkeypatch.setenv("QUIZCRAFT_SECRET_KEY", SECRET)
    recorded = _record_make_llm_client(monkeypatch)

    gen = get_llm_client(session)
    try:
        client = await gen.__anext__()
        assert isinstance(client, MockLLMClient)
        assert recorded[0].llm_model == "db-special"  # 用 DB 配置，非 env 默认 gpt-4o
    finally:
        await gen.aclose()


async def test_get_llm_client_falls_back_to_env(session, monkeypatch):
    """DB 无配置 → get_llm_client 用 env 配置构建 client（捕获到 env 默认 model）。"""
    recorded = _record_make_llm_client(monkeypatch)

    gen = get_llm_client(session)
    try:
        client = await gen.__anext__()
        assert isinstance(client, MockLLMClient)
        assert recorded[0].llm_model == "gpt-4o"  # env 默认
    finally:
        await gen.aclose()


# ---------- 路由集成：真实 async-gen get_llm_client 经 Depends 解析 ----------


async def _seed_document(session) -> int:
    """直接往 DB 插一份带分块的文档（同 test_quiz_api，聚焦 LLM 配置而非解析）。"""
    doc = Document(filename="lecture.pdf", page_count=1, status=DocumentStatus.COMPLETE)
    session.add(doc)
    await session.flush()
    section = Section(
        document_id=doc.id,
        section_path="第2章 光合作用",
        page_number=12,
        content="光合作用是植物利用光能合成有机物的过程。光反应发生在类囊体膜上。",
        order_index=0,
        token_count=20,
    )
    session.add(section)
    await session.commit()
    return doc.id


STEP1 = (
    '{"concepts": [{"name": "光合作用", "description": "植物利用光能合成有机物", '
    '"bloom_level": "记忆", "source_text": "光合作用是植物利用光能合成有机物的过程。"}]}'
)
STEP2 = (
    '{"questions": [{"stem": "光反应发生在？", "options": ["细胞核", "类囊体膜", "细胞壁", "液泡"], '
    '"correct_option_index": 1, "explanation": "光反应在类囊体膜", "bloom_level": "记忆", '
    '"difficulty": "easy", "source_text": "光反应发生在类囊体膜上。"}]}'
)
EVAL_HIGH = '{"accuracy": 0.9, "source_grounding": 0.9}'


async def test_route_uses_db_llm_config_at_runtime(session, client, monkeypatch):
    """端到端：DB 存配置 → generate-quiz 路由经真实 get_llm_client（async gen）读 DB 配置。

    不请求 llm_mock（不 override get_llm_client），让真实 async-gen 依赖经 Depends 解析——
    证明接线 + DB 配置生效。monkeypatch make_llm_client 捕获 settings 并返回带预设响应的 mock。
    若回退 env，captured.llm_model 会是默认 gpt-4o 而非 DB 的 db-special。
    """
    monkeypatch.setenv("QUIZCRAFT_SECRET_KEY", SECRET)
    # DB 配置：mock provider + 特殊 model，便于与 env 默认 gpt-4o 区分
    await save_llm_config(
        session,
        LLMConfig(provider="mock", api_key=None, model="db-special"),
        SECRET,
    )
    doc_id = await _seed_document(session)

    captured: list[Settings] = []
    mock = MockLLMClient(responses=[STEP1, STEP2, EVAL_HIGH])

    def fake_make(settings):
        captured.append(settings)
        return mock

    import quizcraft.dependencies as deps

    monkeypatch.setattr(deps, "make_llm_client", fake_make)

    resp = await client.post(f"/api/documents/{doc_id}/generate-quiz")

    assert resp.status_code == 201, resp.text
    assert len(resp.json()["questions"]) >= 1
    # 关键：路由用的是 DB 配置（db-special），非 env 默认 gpt-4o
    assert captured, "make_llm_client 未被调用，get_llm_client 未经 Depends 解析"
    assert captured[0].llm_model == "db-special"


async def test_route_falls_back_to_env_llm_config(session, client, monkeypatch):
    """端到端：DB 无配置 → generate-quiz 路由用 env 配置（默认 model gpt-4o）。"""
    doc_id = await _seed_document(session)

    captured: list[Settings] = []
    mock = MockLLMClient(responses=[STEP1, STEP2, EVAL_HIGH])

    def fake_make(settings):
        captured.append(settings)
        return mock

    import quizcraft.dependencies as deps

    monkeypatch.setattr(deps, "make_llm_client", fake_make)

    resp = await client.post(f"/api/documents/{doc_id}/generate-quiz")

    assert resp.status_code == 201, resp.text
    assert captured
    assert captured[0].llm_model == "gpt-4o"  # env 默认，未配置 DB
