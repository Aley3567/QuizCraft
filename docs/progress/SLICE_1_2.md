# 切片 1.2 进度：LLM 配置与出题增强

> Ralph 循环进度文件，每轮更新。状态活在 git commit + 本文件，不靠对话记忆。

**STATUS: IN PROGRESS**

## 当前状态

子系统 1 后端 + 子系统 2 后端 + 子系统 3 简答评分后端完成。累计 131 测全绿（新增 20 测）。

- 子系统 1 后端：API key Fernet 加密存储 + KV settings 表 + GET/POST /api/settings/llm + 连通测试
- 子系统 2 后端：出题参数 number / difficulty_range / question_types / chapter_scope /
  bloom_distribution + Bloom 完整四层（记忆/理解/应用/分析）+
  POST /api/documents/{id}/generate-quiz 接受可选 body（无 body 退回切片 1.1 默认行为）
- 子系统 3 后端：简答题型生成（short_answer）+ LLM rubric 评分 0-1 + 引用文档反馈 +
  Answer 按题型分流（选择确定性判分 / 简答 LLM 评分）+ 混合会话结算

前端 Settings UI、运行时出题/答题改用 DB 配置、题目预览编辑、交叉出题、
完整 6 维自评——均待后续轮次。

## 已完成

### 2026-06-24 轮次 1：LLM 配置后端核心（加密存储 + API + 连通测试）

TDD（先红后绿），29 个新测试，累计 100 全绿。一个 commit。

**加密服务（`services/settings/crypto.py`，纯逻辑）**
- `derive_fernet_key(secret)`：SHA-256 派生 Fernet key（32 字节 → urlsafe base64）
- `encrypt/decrypt`：Fernet 对称加解密（AES128-CBC + HMAC），覆盖 CJK
- `encrypt_or_none/decrypt_or_none`：None 透传（API key 可选字段不强制加密）
- 空 secret 拒绝派生——不 fallback 弱密钥，避免明文落库敏感凭证
- 依赖：`uv add cryptography`（49.0.0，带 cffi 传递依赖）

**KV 存储模型（`models/setting.py`）**
- `Setting`：key(主键) + value(Text JSON)，单行 KV 存 LLM 配置
- 注册到 `models/__init__`，conftest create_all + lifespan create_all 均覆盖建表

**配置存取服务（`services/settings/store.py`）**
- `LLMConfig` dataclass：provider/api_key(明文)/model/base_url（内存表示，落库前加密）
- `LLMConfigView` dataclass：provider/has_api_key/model/base_url（脱敏视图，GET 用）
- `save_llm_config(session, config, secret)`：加密 api_key + upsert（同 key 覆盖）；
  api_key 非空但 secret 空 → 抛 ValueError（调用方转 400）
- `load_llm_config(session, secret)`：读 + 解密回明文（运行时构建 client 用）
- `load_llm_config_view(session)`：读脱敏视图（不解密，不暴露明文 key，不需 secret）

**连通测试服务（`services/settings/connection.py`）**
- `check_llm_connection(provider, api_key, model, base_url) -> ConnectionResult`：
  构造临时 client + 发一次 ping，捕获构造与调用的一切异常为 ok=False（不 500）
- mock provider 直接 ok=True；openai 真实调用，失败仅报告不阻断保存
- **关键修复（真机冒烟发现）**：原 `except ValueError` 只捕获构造期 ValueError，
  本机 SOCKS 代理环境 `AsyncOpenAI` 构造抛 `ImportError`（缺 socksio）逃逸 → 500。
  测试 monkeypatch `make_llm_client` 是盲区。合并为 `except Exception` 捕获构造+调用，
  详见 `.codex-loop/ralph-review-notes.md`

**配置 schema + 路由（`schemas/settings.py` + `routers/settings.py`）**
- `LLMConfigRequest`（POST body）/ `LLMConfigOut`（GET 脱敏）/ `ConnectionResultOut` /
  `LLMConfigSaveResponse`（config + connection）
- `GET /api/settings/llm`：返回脱敏视图，未配置 404
- `POST /api/settings/llm`：保存（加密）+ 立即连通测试，返回脱敏视图 + 连通结果；
  明文 api_key 永不离开后端（响应文本全程无明文 key，冒烟 + 测试双重验证）
- `config.py` 加 `secret_key`（从 `QUIZCRAFT_SECRET_KEY` 读，未配置时加密写入含 key 配置被拒）
- main 装配 settings_router

**测试**：test_settings_crypto（8）/ test_settings_store（10）/ test_settings_connection（6）/ test_settings_api（5）

**真机冒烟**（uvicorn mock provider，独立 db + secret）：
- GET 未配置 → 404 ✓
- POST mock 配置 → 200 + 脱敏视图 + connection.ok=True ✓
- POST 后 GET → 读回脱敏配置（has_api_key=True 但响应无明文 key）✓
- 有 secret + openai+key + SOCKS 代理环境 → 200 + connection.ok=False + 清晰 message（配置仍保存，不 500）✓
- 无 secret + openai+key → 400 "secret 不能为空"（拒绝明文落库）✓
- 无 secret + mock 无 key → 200（不需 secret）✓

### 2026-06-24 轮次 2：出题参数控制后端（子系统 2 核心增量）

TDD（先红后绿），11 个新测试（4 prompt + 4 generator + 3 API），累计 111 全绿。一个 commit。

**出题参数 schema（`schemas/quiz.py`）**
- `QuizGenerationRequest`：number / difficulty_range / question_types / chapter_scope /
  bloom_distribution / concepts_per_section / questions_per_concept，全可选
- 无 body 时退回切片 1.1 默认行为（向后兼容现有调用与测试）

**纯逻辑层扩展（`services/quiz/generator.py` + `prompts.py`）**
- `generate_quiz` 新增关键字参数：number / difficulty_range / question_types / bloom_distribution
- `filter_sections_by_scope(sections, chapter_scope)`：纯函数，按 section_path 子串白名单过滤
  （None/空=全部；多关键词任一匹配即纳入；duck-typed 兼容 Section ORM 与 SectionData）
- difficulty 过滤：自评前剔除不在 difficulty_range 的题，filtered_count 计数
  （避免对不要的题浪费自评 LLM 调用）
- number 截断：自评后截断到目标数，保留高分题
- Bloom 扩展完整四层（记忆/理解/应用/分析，原仅记忆/理解）；prompt 要求 explanation 开头简述为何定该层级
- prompt 透传 difficulty_range（显式列举允许难度 + "只能取"）、question_types、bloom_distribution（百分比分布）
- `QuizGenerationResult` 加 `filtered_count` 字段

**路由（`routers/quiz.py`）**
- `generate_quiz_for_document` 接受可选 `body: QuizGenerationRequest | None = Body(default=None)`
- question_types 校验：调 LLM 前校验只含 multiple_choice，其他 → 400
  （题型生成与评分方式绑定，留后续子系统）
- chapter_scope 过滤后无可出题分块 → 400
- 透传全部参数给 generate_quiz

**测试**：test_quiz_prompts（+4）/ test_quiz_generator（+4：difficulty 过滤、number 截断、
filter_sections_by_scope×2）/ test_quiz_api（+3：number 截断、不支持的题型 400、chapter_scope 过滤生效）

**未做（明确留后续）**：question_types 真正多题型生成（true_false/fill_blank/short_answer）——
判断=选择题特例、填空=精确匹配、简答=LLM 评分，与评分方式绑定，留子系统 3（简答评分）配套。
前端出题配置面板留前端轮次。

### 2026-06-24 轮次 3：简答评分后端核心（子系统 3）

TDD（先红后绿），20 个新测试（2 prompts + 4 generator + 6 short_answer + 6 answer_api + 2 quiz_api），
累计 131 全绿。一个 commit。

**数据模型扩展（`models/quiz.py`）**
- `QuestionType` 增加 `SHORT_ANSWER`
- `Question.correct_option_index` 改可空（简答题无正确下标）；新增 `answer_text`（简答参考答案/rubric）
- `Answer` 新增 `short_answer_text`（学生作答文本）+ `score`（0-1 简答 LLM 评分）

**出题引擎扩展（`services/quiz/generator.py` + `prompts.py`）**
- `GeneratedQuestion` 加 `question_type` + `answer_text`，`correct_option_index` 可空
- `generate_quiz` 按 `question_types` 分支生成：multiple_choice 走 `build_step2_messages`，
  short_answer 走新 `build_step2_short_answer_messages`（生成 stem + answer_text + source_text）
- 题型去重保序；`_build_generated_question` 按题型构造（选择题 options/correct_option_index，
  简答题 answer_text/options=[]/correct=None）
- 简答题跳过生成期自评（评分在答题时由 LLM rubric 完成）；difficulty_range 过滤对简答同样生效

**简答评分服务（`services/quiz/short_answer.py`，新文件，纯逻辑）**
- `ShortAnswerScore` dataclass：score + feedback
- `score_short_answer(question, student_answer, llm)`：调 LLM rubric（`build_short_answer_eval_messages`），
  解析 {score, feedback}；score clamp [0,1]；空响应/解析失败/缺 feedback 走确定性兜底
  （score=0 + 锚定页码/章节/原文反馈，不 500 不阻塞作答）

**Schema + 路由扩展（`schemas/quiz.py` + `routers/quiz_sessions.py` + `routers/quiz.py`）**
- `QuestionOut` 加 `answer_text`（预览用，答题视图防泄露留子系统 4，与 correct_option_index 一致）
- `AnswerRequest` 加 `short_answer_text`（selected_option_index 改可选，按题型分流）
- `AnswerOut` 加 `score` + `short_answer_text`
- `submit_answer` 按 `question.question_type` 分流：选择题 selected_option_index 确定性判分 +
  generate_feedback；简答题 short_answer_text 经 score_short_answer 评 0-1 + feedback
- 混合会话结算：选择题 is_correct 计 1，简答题 score 计分，
  `score = (选择题正确数 + 简答分数和) / 总题数`；幂等 upsert 覆盖五字段
- quiz router `SUPPORTED_QUESTION_TYPES` 扩展含 short_answer；落库按 `gq.question_type` 设字段

**测试**：test_quiz_prompts（+2）/ test_quiz_generator（+4：简答生成/混合/跳过自评/difficulty 过滤）/
test_short_answer（+6 新文件：评分/兜底/缺 feedback/clamp）/ test_answer_api（+6：简答返回/兜底/
缺文本 400/单题结算/混合结算 0.75/幂等）/ test_quiz_api（+2：简答生成/answer_text 落库）

**真机冒烟**（uvicorn mock provider + 独立 db + ORM seed 简答题 + POST /answer）：
- POST 简答 → 200 + score=0（mock 空响应兜底）+ is_correct=None + short_answer_text 回显 +
  feedback 含页码 12 + 原文 ✓
- 冒烟脚本客户端 httpx 受本机 SOCKS 代理影响需 `trust_env=False`（非产品 bug，详见 review-notes）

**未做（明确留后续）**：
- 异步评分轮询（任务清单写异步 + 前端轮询）：本轮做同步评分（提交即返回），异步状态机留真实 LLM
  接入后再做（mock 秒级返回；真实 LLM 耗时是 blocker）
- 真正多题型 true_false/fill_blank 生成（留配套评分方式）

## 子系统进度（按 SLICE_PHASE_1.md 切片 1.2 任务清单）

- [~] 1. LLM 配置 UI 与后端（Settings 页 + provider/key/model/base_url 存 SQLite settings 表 + POST /api/settings/llm + 测试调用连通验证）
  - [x] 后端：加密存储 + KV 表 + GET/POST API + 连通测试 —— 轮次 1
  - [ ] 前端 Settings 页（provider 选择 + key 输入 + model/base_url + 测试按钮）
  - [ ] 运行时出题/答题改用 DB 配置（get_llm_client 读 settings 表，fallback env）
- [ ] 2. 出题参数控制（number/difficulty_range/question_types/chapter_scope/bloom_distribution API + 前端面板 + Bloom 完整 4 层）
  - [x] 后端：参数 schema + generate_quiz 扩展 + prompt Bloom 四层 + POST body + 测试 —— 轮次 2
  - [ ] 前端出题配置面板（选择题数/难度/题型比例/章节范围）
  - [ ] 真正多题型生成（true_false/fill_blank/short_answer，留子系统 3 配套评分）
- [ ] 3. 简答题生成与评分（short_answer 题型 + LLM rubric 评分 + 异步轮询）
  - [x] 后端：short_answer 题型生成 + LLM rubric 评分 0-1 + 引用文档反馈 + Answer 按题型分流 + 混合会话结算 —— 轮次 3
  - [ ] 异步评分 + 前端轮询（同步评分已通，异步状态机留真实 LLM 接入后）
- [ ] 4. 题目预览与编辑（预览模式 + 编辑/删除 + 确认进练习池）
- [ ] 5. 交叉出题 + 标记坏题（按 concept/type 交叉混合 + 坏题移出练习池）
- [ ] 6. 完整自我批评管线（6 维度自评 + 可配淘汰阈值）

## 验收标准核对

- [ ] Web UI Settings 页配置 LLM provider + API key 后，测试调用成功 —— 后端 API + 连通测试已通；前端 UI 待
- [ ] 出题时可选择题型/难度/数量/章节范围 —— 子系统 2 后端已通；前端面板待
- [x] 简答题提交后 LLM 评分返回 0-1 + 引用文档解释 —— 子系统 3 后端（同步评分；异步轮询留后续）
- [ ] 题目生成后可预览/编辑/删除，确认后进练习池 —— 子系统 4
- [ ] 答题时题目顺序交叉混合 —— 子系统 5
- [ ] 可标记坏题 —— 子系统 5
- [ ] 完整 6 维度自评 + 可配阈值 —— 子系统 6

## 还剩

切片 1.2 子系统 1-3 后端完成（LLM 配置 + 出题参数 + 简答评分），剩余子系统 1 前端 + 子系统 2 前端/多题型 +
子系统 3 异步轮询 + 子系统 4-6。
下一轮优先做子系统 1 前端 Settings 页（打通"配置→测试"端到端 UI），
或子系统 6 完整 6 维自评（纯逻辑层，TDD 友好，无需前端），
或子系统 1 后端增量"运行时改用 DB 配置"（让已存 DB 配置生效）。

## Blockers

- **真实 LLM key**：连通测试的 openai provider 真实路径需真实 key + 网络。本机 SOCKS 代理环境
  `AsyncOpenAI` 构造缺 socksio 会失败——已优雅降级为 ok=False + message（非 500），真实部署需 yufeng
  注意装 `httpx[socks]` 或清代理（同切片 1.1 blocker）。真实连通质量 + 简答 rubric 评分质量
  待 yufeng 真实 key 验证。
- **QUIZCRAFT_SECRET_KEY 部署**：加密 API key 需配置 secret。未配置时含 key 的配置被 400 拒绝（保护性）；
  mock provider 无 key 不受影响。自部署务必配置（生产安全基线）。
- **运行时 LLM 配置来源**：本轮 DB 配置已可存可读，但运行时出题/答题仍走 `get_llm_client()`（env 配置）。
  让运行时优先读 DB settings（fallback env）是下一增量，需改 `get_llm_client` 依赖为 async 读 DB——
  涉及现有所有路由的 LLM 依赖签名变更，单独一轮做更稳妥。
- **异步简答评分轮询**：本轮同步评分（提交即返回 score+feedback）。真实 LLM 评分耗时数秒到数十秒，
  同步会阻塞 HTTP。异步状态机（Answer pending→scored）+ 轮询端点留真实 LLM 接入后再做。
- **前端浏览器人机交互**：无 Playwright 自动化，Settings 页/简答作答 UI 待 yufeng `cd frontend && npm run dev` 实地验证。
