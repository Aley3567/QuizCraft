# 切片 1.1 进度：最小出题闭环

> Ralph 循环进度文件，每轮更新。状态活在 git commit + 本文件，不靠对话记忆。

## 当前状态

进行中 —— 子系统 1「后端骨架」完成，下一轮做子系统 2「文档解析」。

## 已完成

### 2026-06-24 轮次：后端骨架 + 数据模型 + LLM 抽象层

项目从零搭建，TDD（先红后绿），12 个测试全绿。

- **项目脚手架**：uv + pyproject.toml，依赖装齐
  （fastapi / sqlalchemy[asyncio] / aiosqlite / openai / pymupdf / pytest-asyncio / httpx）
- **FastAPI 应用入口**（`main.py`）+ `/health` 端点
- **SQLAlchemy async 基座**（`db.py`）：`Base`（AsyncAttrs）+ `TimestampMixin` + `make_engine` / `make_session_factory`
- **数据模型建表**（`models/`）：Document / Section / Concept / Question / QuizSession / Answer
  - 枚举：`DocumentStatus` / `QuestionType` / `SessionStatus`
  - `source_span` JSON 字段（Concept / Question 携带文档原文位置 {page, section_path, text}）
  - `Question.options` / `QuizSession.question_ids` JSON 字段
  - 外键级联删除（document -> section/concept/question -> quiz_session -> answer）
- **LLM 抽象层**（`services/llm/`）：`LLMClient` Protocol + `Message` / `LLMResponse` + `MockLLMClient` + `OpenAICompatibleClient` + `make_llm_client` 工厂
  - 默认 provider=mock，测试不依赖真实 key
  - OpenAI 兼容实现覆盖 Claude/GPT（via base_url），Ollama 延后
- **配置层**（`config.py`）：`Settings` 从 `QUIZCRAFT_` 环境变量读取（db_url / llm_provider / llm_api_key / llm_model / llm_base_url）
- **依赖注入**（`dependencies.py`）：`get_session` / `get_llm_client`
- **测试**：`conftest.py`（内存 SQLite + httpx ASGITransport）+ test_models / test_llm / test_app

## 子系统进度（按 SLICE_PHASE_1.md 切片 1.1 任务清单）

- [x] 1. 后端骨架（FastAPI 分层 + SQLite + 数据模型 + LLM 抽象层接口）—— 本轮
- [ ] 2. 文档解析（PyMuPDF4LLM 提取 + 512-1024 token 结构分块 + POST /api/documents）
- [ ] 3. 出题引擎（两步生成 Step1 Concepts / Step2 选择题 + POST /generate-quiz + 简化自评）
- [ ] 4. 答题反馈（POST /quiz-sessions/{id}/answer + 即时判分 + LLM 引用原文反馈）
- [ ] 5. 前端（Next.js App Router + 上传页 + 答题界面 + 错题反馈展示）
- [ ] 6. 端到端集成测试（LLM mock，SQLite 内存）

## 验收标准核对

- [ ] 上传 PDF（10-50 页）2 分钟内解析 —— 待子系统 2
- [ ] 生成 5-10 道选择题，每题显示来源页码和章节 —— 待子系统 3
- [ ] 选择题答完即时判分 —— 待子系统 4
- [ ] 错题反馈引用课件原文 —— 待子系统 4
- [x] 全流程 API 集成测试基础设施就绪（LLM mock + SQLite 内存）；端到端用例待子系统 6

## 还剩

子系统 2-6（见上）。下一轮从子系统 2「文档解析」开始：PyMuPDF4LLM 提取 PDF、结构感知分块、上传 API。

## Blockers

- **真实 LLM key**：暂用 MockLLMClient 覆盖全部 LLM 调用，provider/key 配置留给 yufeng。OpenAICompatibleClient 真实调用需真实 key，本轮未验证（测试只验证构造与路由）。
- **SOCKS 代理环境**：本机带 SOCKS 代理时，openai SDK 构造 AsyncOpenAI 会创建 httpx client 并因缺 socksio 失败——非本代码问题，测试已用 monkeypatch 清代理规避；真实部署需 yufeng 注意。
