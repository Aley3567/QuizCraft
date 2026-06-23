# 切片 1.1 进度：最小出题闭环

> Ralph 循环进度文件，每轮更新。状态活在 git commit + 本文件，不靠对话记忆。

## 当前状态

进行中 —— 子系统 1-3 完成（后端骨架 / 文档解析 / 出题引擎），下一轮做子系统 4「答题反馈」。

## 已完成

### 2026-06-24 轮次 1：后端骨架 + 数据模型 + LLM 抽象层

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

### 2026-06-24 轮次 2：文档解析（L1 提取 + 结构分块 + 上传 API）

TDD，24 个新测试，累计 36 全绿。两个 commit：

**commit A — 解析服务（`services/parsing/`）**
- `tokens.estimate_tokens`：CJK 按字 + 其余 4 字符比例（分块尺寸控制用，非计费口径；真实 tokenizer 留切片 1.2）
- `chunker.chunk_pages`：header 栈维护 section_path（跨页保持、同级替换、嵌套），512-1024 token，
  段落→句子→字符三级回退拆分；**关键 bug 修复**：边界判断改用候选拼接串的真实估算值，
  非逐单元累加（否则 \n\n 与标点的 rest//4 进位会让块超 1024）
- `pdf.parse_pdf_to_sections`：pymupdf4llm **经典路径**（`use_layout(False)` 关掉 layout+OCR 重管线，
  干净数字 PDF 无需 Tesseract）按页提取 markdown，`page_chunks=True` 每页带 1-indexed `metadata.page` + `text`
- 依赖：pyproject 加 `pymupdf4llm>=1.27`，uv.lock 同步（带 numpy/onnxruntime 等传递依赖）
- 测试：test_tokens / test_chunker / test_parsing_pdf（真实生成 PDF 端到端，不依赖外部文件）

**commit B — 上传/查询 API（`schemas/` + `routers/`）**
- `schemas/document.py`：SectionOut / DocumentOut / DocumentDetail（from_attributes 从 ORM 构建）
- `routers/documents.py`：
  - `POST /api/documents`：接受 PDF（扩展名或 content-type 校验）→ L1 解析 + 分块 → 落库 Document+Sections
    （status pending->complete）；解析失败标 FAILED 返 422
  - `GET /api/documents/{id}`：取文档详情含按 order_index 排序的 sections
- `main.py` 装配 documents_router
- 切片 1.1 请求内**同步**解析（秒级，满足「2 分钟内」验收）；异步解析 + 进度轮询、原文件落盘留给切片 1.4
- 测试 helper `_pdf_helper.py` 共用；5 个 API 测试（上传/溯源字段/查询排序/404/非 PDF 拒绝）

### 2026-06-24 轮次 3：出题引擎（两步生成 Step1/Step2 + 简化自评 + POST /generate-quiz）

TDD（先红后绿），15 个新测试，累计 51 全绿。一个 commit。

- **出题 prompt 构建**（`services/quiz/prompts.py`）：Step1 提取 Concepts / Step2 生成选择题 / 自评三套
  prompt，均要求 LLM 严格只返回 JSON + 来源锚定（source_text 引用文档原文）；prompt 函数
  只需 duck-typed 对象，不依赖 ORM
- **出题引擎**（`services/quiz/generator.py`，纯逻辑不碰 DB）：
  - `generate_quiz(sections, llm, *, concepts_per_section=5, questions_per_concept=2, self_eval_threshold=0.6)`
  - Step1：逐分块 LLM 提取 Concepts，补全 `source_span={page, section_path, text}`
  - Step2：逐概念 LLM 生成选择题（Bloom 记忆/理解层），每题带 source_span
  - Step3 简化自评：每题 LLM 评 accuracy + source-grounding，均值 < 阈值淘汰（完整 6 维度延后切片 1.2）；
    `self_eval_threshold=None` 可跳过自评；自评解析失败保守保留题目不打分
  - LLM 返回 JSON 容错：`_extract_json` 剥离 markdown fence + 取首尾大括号，解析失败跳过不中断
  - 数据类带 section_index/concept_index，供 router 落库建外键（不污染纯逻辑层）
- **出题 API**（`routers/quiz.py` + `schemas/quiz.py`）：
  - `POST /api/documents/{id}/generate-quiz`：查 Document（404）/ Sections（400 无分块）→ 两步生成 →
    落库 Concepts/Questions + 新建 QuizSession(in_progress) → 返回 quiz_session + questions + concepts
  - `QuestionOut` 含 correct_option_index（出题后预览/集成测试用）；答题前端视图不含答案版留切片 1.4
- **支撑改动**：`MockLLMClient.set_responses`（测试动态注入 LLM 输出）；conftest 加 `llm_mock` fixture
  （依赖 client，override get_llm_client）；main 装配 quiz_router
- **代码质量**：ruff 检查顺手清理前轮遗留 unused import（dependencies.py 的 Settings、test_chunker.py 的 pytest）
- **测试**：test_quiz_prompts（3）/ test_quiz_generator（8，纯逻辑）/ test_quiz_api（4，端到端落库 + 404/400）

## 子系统进度（按 SLICE_PHASE_1.md 切片 1.1 任务清单）

- [x] 1. 后端骨架（FastAPI 分层 + SQLite + 数据模型 + LLM 抽象层接口）—— 轮次 1
- [x] 2. 文档解析（PyMuPDF4LLM 提取 + 512-1024 token 结构分块 + POST /api/documents）—— 轮次 2
- [x] 3. 出题引擎（两步生成 Step1 Concepts / Step2 选择题 + POST /generate-quiz + 简化自评）—— 轮次 3
- [ ] 4. 答题反馈（POST /quiz-sessions/{id}/answer + 即时判分 + LLM 引用原文反馈）
- [ ] 5. 前端（Next.js App Router + 上传页 + 答题界面 + 错题反馈展示）
- [ ] 6. 端到端集成测试（LLM mock，SQLite 内存）

## 验收标准核对

- [ ] 上传 PDF（10-50 页）2 分钟内解析 —— 解析同步且快，但**仅用生成的小 PDF（1-2 页）测过**；真实 10-50 页课件 PDF 端到端计时待真实 fixture 验证（机制已通）
- [x] 生成选择题，每题显示来源页码和章节 —— 子系统 3 已实现（Step2 生成带 source_span{page, section_path, text}，API 响应与落库均含）；数量取决于 section 数与 mock，真实 LLM 出题数量/质量/Bloom 分布待真实 key 验证
- [ ] 选择题答完即时判分 —— 待子系统 4
- [ ] 错题反馈引用课件原文 —— 待子系统 4
- [x] 全流程 API 集成测试基础设施就绪（LLM mock + SQLite 内存）；上传+解析、出题端到端用例已绿；端到端全链路（出题→答题）待子系统 6

## 还剩

子系统 4-6（见上）。下一轮从子系统 4「答题反馈」开始：
- POST /api/quiz-sessions/{id}/answer：接收 selected_option_index
- 即时判分（确定性，对照 Question.correct_option_index），落库 Answer(is_correct)
- LLM 根据用户答案 + source_span 生成引用文档原文的反馈（Answer.feedback）
- QuizSession 记录答题结果，答完置 status=completed + score
- 全程 MockLLMClient

## Blockers

- **真实 LLM key**：暂用 MockLLMClient 覆盖全部 LLM 调用，provider/key 配置留给 yufeng。OpenAICompatibleClient 真实调用需真实 key，未验证（测试只验证构造与路由）。
- **SOCKS 代理环境**：本机带 SOCKS 代理时，openai SDK 构造 AsyncOpenAI 会创建 httpx client 并因缺 socksio 失败——非本代码问题，测试已用 monkeypatch 清代理规避；真实部署需 yufeng 注意。
- **真实 10-50 页课件 PDF fixture**：本轮解析用 pymupdf 生成的内存 PDF（china-s CJK 字体）验证；真实课件 PDF（含复杂排版/扫描页）的解析质量待 yufeng 提供样本验证，L2/L3 分层路由在切片 1.4。
- **pymupdf4llm 安装**：本轮已 `uv pip install pymupdf4llm` 成功并写入 pyproject + uv.lock；它带 numpy/onnxruntime 等传递依赖（layout 检测用），切片 1.1 走经典路径未实际用到这些，但依赖已落定。
- **出题数量与质量**：mock LLM 每分块默认出 5 概念、每概念 2 题，自评阈值默认 0.6（accuracy+source-grounding 均值）。真实 LLM 出题数量/质量/Bloom 分布/干扰项是否真基于常见误解待 yufeng 真实 key 验证；完整 6 维度自评与可配阈值延后切片 1.2。
- **正确答案暂含于 generate-quiz 响应**：`QuestionOut` 当前含 correct_option_index（出题后预览/集成测试用），尚未做"答题前端不含答案"的视图拆分，留切片 1.4 答题反馈子系统补 AttemptView。
