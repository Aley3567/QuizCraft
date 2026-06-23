# 切片 1.1 进度：最小出题闭环

> Ralph 循环进度文件，每轮更新。状态活在 git commit + 本文件，不靠对话记忆。

## 当前状态

进行中 —— 子系统 1-5 完成（后端骨架 / 文档解析 / 出题引擎 / 答题反馈 / 前端），下一轮做子系统 6「端到端集成测试」。后端 69 测 + 前端 21 测全绿；前后端真机冒烟（CORS + 上传 + 出题端点）已通。

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

### 2026-06-24 轮次 4：答题反馈（即时判分 + LLM 引用原文反馈 + 会话结算）

TDD（先红后绿），15 个新测试，累计 66 全绿。一个 commit。

- **反馈 prompt**（`services/quiz/prompts.py` 加 `build_feedback_messages`）：要求 LLM 据学生作答 +
  source_span（页码/章节路径/原文片段）生成引用课件原文的解释，强调「非通用解析」；只返回纯文本
- **反馈生成**（`services/quiz/feedback.py`，纯逻辑不碰 DB）：
  - `generate_feedback(question, *, selected_option_index, is_correct, llm)` 调 LLM，空响应/异常走 `_fallback_feedback`
    —— 判分不依赖 LLM，LLM 抖动不丢反馈
  - `_fallback_feedback` 确定性兜底：含判定 + 正确答案文本 + 来源页码/章节/原文片段；source_span 缺失也容错
- **答题 schema**（`schemas/quiz.py` 加 `AnswerRequest` / `AnswerOut`）：
  - `AnswerRequest{question_id, selected_option_index}` —— 带 question_id（非按序自动推进），作答明确、可重答、可乱序，
    便于切片 1.2 交叉混合出题与重答
  - `AnswerOut` 不含 correct_option_index：前端经 is_correct + feedback 文本理解对错，正确答案不下标暴露（防泄露）
- **答题 API**（`routers/quiz_sessions.py` 新建，prefix /api/quiz-sessions）：
  - `POST /api/quiz-sessions/{id}/answer`：404 会话不存在 / 400 已结束 / 400 题目不属于该会话 / 404 题目不存在 /
    422 选项越界 → 确定性判分（selected == correct）→ LLM 反馈 → 幂等落库 Answer（同 session+question 已有则更新）→
    答完全部题结算 status=completed + score=正确数/总数 + completed_at
- **装配**：`routers/__init__` 导出 quiz_sessions_router；main include_router
- **设计取舍**：会话答完即 completed，completed 后拒绝重答（400）；幂等价值在于「未答完前同题重提交不新增 Answer」
  （网络重试/改答案），测试用 n=2 覆盖该路径
- **测试**：test_quiz_feedback（6：prompt 含判定/页码/原文 / LLM 内容采用 / 空响应兜底 / 正错分支 / 缺 source_span）+
  test_answer_api（9：答对仍 in_progress / 答错 / 答完结算 score=0.5 / 幂等重答覆盖 / LLM 空兜底 / 404 / 400 已结束 /
  400 不属于 / 422 越界）

### 2026-06-24 轮次 5：前端子系统（Next.js + 上传/答题/错题反馈）+ CORS + 真机建表修复

TDD（纯逻辑先红后绿），前端 21 测全绿、tsc 类型检查通过、next build 通过、前后端真机冒烟通；后端新增 3 测、累计 69 全绿。一个 commit。

- **后端 CORS 中间件**（`config.py` 加 `cors_origins` 默认 `["http://localhost:3000"]` + `main.py` 装 `CORSMiddleware`）：前端 dev server (:3000) 跨域调后端必需。3 测：预检 OPTIONS 放行 / 实际请求回写 allow-origin / 未配置源不放行
- **后端 lifespan 启动建表**（`main.py` 加 `lifespan` → `Base.metadata.create_all` + `_ensure_data_dir`）：**真机冒烟发现的运行时 bug**——ASGITransport 测试（conftest create_all）掩盖了 dev 首启无表，首次上传 INSERT 命中无表 500。最小修复，不影响 ASGITransport 测试（不触发 startup）。详见 `.codex-loop/ralph-review-notes.md`
- **前端项目骨架**（`frontend/`，手动 scaffold）：Next.js 15 App Router + React 19 + TypeScript + vitest；package.json/tsconfig/next.config/vitest.config/.gitignore；npm install 67 包成功
- **前端类型层**（`lib/types.ts`）：对齐后端 Pydantic schema（DocumentDetail/QuestionOut/AnswerOut 等）；`QuestionOut.correct_option_index` 类型存在但 UI 刻意不渲染（防答案泄露，对齐答题视图设计）
- **前端纯逻辑**（`lib/quiz-state.ts` + `lib/api.ts`，抽离自组件便于单测）：
  - quiz-state：`isQuizComplete` / `computeScore` / `wrongQuestions` / `formatSourceSpan`（「第X页（章节）」式引用）/ `sourceExcerpt`（超长截断）
  - api：`apiBaseUrl`（env 覆盖，默认 :8000）/ `buildAnswerBody` / `parseApiError`（FastAPI detail 归一化）/ `uploadDocument`·`generateQuiz`·`submitAnswer` fetch 封装 / `ApiError`
- **前端 UI**（`app/page.tsx` 单页状态机 idle→uploaded→quizzing→done + 4 组件）：
  - `Uploader`：拖拽/选择 PDF 上传
  - `DocumentSummary`：文档信息 + 分块明细折叠
  - `QuizPlayer`：一题一题答，选完即判分 + 引用原文/页码反馈，确认推进下一题
  - `ResultView`：总分 + 错题列表（每题 stem + 你的选择 + feedback + 来源原文/页码）
- **测试**：前端 vitest 21 测（quiz-state 14 + api 7）全绿；`tsc --noEmit` 通过；`next build` 成功（4/4 静态页）
- **真机冒烟**（后端 uvicorn :8011 mock provider）：/health 200 + CORS 头正确（allow-origin/methods/headers）+ POST /api/documents 201（上传 pymupdf 生成的小 PDF，返回文档详情+分块）+ POST generate-quiz 201（mock 空内容→0 题，端点可达、结构合法）。前端 dev 浏览器交互（Playwright）未做，留 yufeng 人工或子系统 6

## 子系统进度（按 SLICE_PHASE_1.md 切片 1.1 任务清单）

- [x] 1. 后端骨架（FastAPI 分层 + SQLite + 数据模型 + LLM 抽象层接口）—— 轮次 1
- [x] 2. 文档解析（PyMuPDF4LLM 提取 + 512-1024 token 结构分块 + POST /api/documents）—— 轮次 2
- [x] 3. 出题引擎（两步生成 Step1 Concepts / Step2 选择题 + POST /generate-quiz + 简化自评）—— 轮次 3
- [x] 4. 答题反馈（POST /quiz-sessions/{id}/answer + 即时判分 + LLM 引用原文反馈 + 会话结算）—— 轮次 4
- [x] 5. 前端（Next.js App Router + 上传页 + 答题界面 + 错题反馈展示）—— 轮次 5
- [ ] 6. 端到端集成测试（LLM mock，SQLite 内存）

## 验收标准核对

- [ ] 上传 PDF（10-50 页）2 分钟内解析 —— 解析同步且快，但**仅用生成的小 PDF（1-2 页）测过**；真实 10-50 页课件 PDF 端到端计时待真实 fixture 验证（机制已通）
- [x] 生成选择题，每题显示来源页码和章节 —— 子系统 3 已实现（Step2 生成带 source_span{page, section_path, text}，API 响应与落库均含）；数量取决于 section 数与 mock，真实 LLM 出题数量/质量/Bloom 分布待真实 key 验证
- [x] 选择题答完即时判分 —— 子系统 4（确定性判分 selected==correct + Answer 落库 + 会话 status=completed/score 结算）
- [x] 错题反馈引用课件原文 —— 子系统 4（LLM 据 source_span 生成引用原文反馈；空响应/异常走 `_fallback_feedback` 仍含页码/章节/原文片段）；真实 LLM 反馈质量待真实 key 验证
- [x] 全流程 API 集成测试基础设施就绪（LLM mock + SQLite 内存）；上传+解析、出题、答题三套 API 端到端用例均绿；端到端全链路（上传→出题→答题→反馈）串成一条集成测试待子系统 6
- [x] 前端最小 UI（子系统 5）：Next.js 单页状态机（上传 PDF→出题→逐题答题即时反馈→结果+错题引用原文/页码）；tsc 类型检查 + next build 通过、前端纯逻辑 vitest 21 测绿、前后端真机 CORS+上传+出题冒烟通；浏览器人工交互验证待 yufeng（无 Playwright 自动化）

## 还剩

子系统 6（最后一个）：

- **子系统 6 端到端集成测试**：上传 PDF → 出题 → 答题 → 反馈全链路串成一条 pytest 集成测试（LLM mock，SQLite 内存，ASGITransport）。后端三套 API 已各自绿、前端真机冒烟已通，子系统 6 侧重全链路一条用例（mock LLM 注入有效 JSON 响应，验证从上传到错题反馈的完整数据流与 source_span 锚定贯穿）+ 可选前端 Playwright 冒烟。完成后切片 1.1 验收全部通过 → STATUS: COMPLETE

## Blockers

- **真实 LLM key**：暂用 MockLLMClient 覆盖全部 LLM 调用，provider/key 配置留给 yufeng。OpenAICompatibleClient 真实调用需真实 key，未验证（测试只验证构造与路由）。
- **SOCKS 代理环境**：本机带 SOCKS 代理时，openai SDK 构造 AsyncOpenAI 会创建 httpx client 并因缺 socksio 失败——非本代码问题，测试已用 monkeypatch 清代理规避；真实部署需 yufeng 注意。
- **真实 10-50 页课件 PDF fixture**：本轮解析用 pymupdf 生成的内存 PDF（china-s CJK 字体）验证；真实课件 PDF（含复杂排版/扫描页）的解析质量待 yufeng 提供样本验证，L2/L3 分层路由在切片 1.4。
- **pymupdf4llm 安装**：本轮已 `uv pip install pymupdf4llm` 成功并写入 pyproject + uv.lock；它带 numpy/onnxruntime 等传递依赖（layout 检测用），切片 1.1 走经典路径未实际用到这些，但依赖已落定。
- **出题数量与质量**：mock LLM 每分块默认出 5 概念、每概念 2 题，自评阈值默认 0.6（accuracy+source-grounding 均值）。真实 LLM 出题数量/质量/Bloom 分布/干扰项是否真基于常见误解待 yufeng 真实 key 验证；完整 6 维度自评与可配阈值延后切片 1.2。
- **真实 LLM 反馈质量**：答题反馈 mock 返回固定文本；真实 LLM 是否真引用原文片段、措辞是否自然、是否给出「你的课件第 X 页提到…」式溯源待 yufeng 真实 key 验证。兜底 `_fallback_feedback` 确定性含页码/正确答案/原文，保证 LLM 抖动时不丢反馈。
- **答题前端视图拆分**：`AnswerOut` 已不含 correct_option_index（前端经 is_correct + feedback 理解对错）；但出题响应 `QuestionOut` 仍含正确答案（出题后预览/集成测试用）——切片 1.1 后端不单独做「前端不含答案」的视图，留子系统 5 前端在前端层处理（答题界面只取题面+选项，不请求 correct_option_index 即可）。**轮次 5 已落地**：前端 `lib/types.ts` 保留 correct_option_index 类型但 `QuizPlayer`/`ResultView` 刻意不渲染
- **真机首启建表**：轮次 5 真机冒烟发现 dev server 首启未建表（ASGITransport 测试盲区 → 首次上传 500），已在 `main.py` lifespan 加 `Base.metadata.create_all` 修复。生产部署换 Alembic 迁移需 yufeng 决策（切片 1.1 单机原型 create_all 足够）
- **前端浏览器交互验证**：轮次 5 前端经 tsc + build + 纯逻辑 vitest + 真机后端链路冒烟验证，但**未做 Playwright 浏览器自动化**（拖拽上传/答题点击/反馈渲染的人机交互）。留 yufeng 人工 `cd frontend && npm run dev`（后端 `PYTHONPATH=backend uvicorn quizcraft.main:app`）实地验证，或子系统 6 补 Playwright
- **真实 LLM 出题/反馈质量**：前端 + 真机冒烟用 mock provider（默认），mock 无预设响应时出题为空、反馈为兜底文本。真实 LLM 接入（`QUIZCRAFT_LLM_PROVIDER=openai` + key）后端到端 UI 真实出题/反馈质量待 yufeng 验证
