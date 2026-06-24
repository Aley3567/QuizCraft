# 切片 1.2 进度：LLM 配置与出题增强

> Ralph 循环进度文件，每轮更新。状态活在 git commit + 本文件，不靠对话记忆。

**STATUS: IN PROGRESS**

## 当前状态

子系统 1-6 后端完成（含子系统1 运行时 DB 配置增量）+ 出题参数 + 简答评分 + 交叉出题/标记坏题 +
完整 6 维自评 + 题目预览编辑/删除/确认进池。累计 174 测全绿（本轮新增 8 测）。

切片 1.2 可运行后端工作已收口：剩余全是 blocker（前端浏览器人机 / 简答异步轮询需真实 LLM）。
下一轮若 monitor 判定 1.2 后端完成 → 推进切片 1.3（闪卡 FSRS，依赖 1.1+1.2 已满足）。

- 子系统 1 后端：API key Fernet 加密存储 + KV settings 表 + GET/POST /api/settings/llm + 连通测试
- 子系统 2 后端：出题参数 number / difficulty_range / question_types / chapter_scope /
  bloom_distribution + Bloom 完整四层（记忆/理解/应用/分析）+
  POST /api/documents/{id}/generate-quiz 接受可选 body（无 body 退回切片 1.1 默认行为）
- 子系统 3 后端：简答题型生成（short_answer）+ LLM rubric 评分 0-1 + 引用文档反馈 +
  Answer 按题型分流（选择确定性判分 / 简答 LLM 评分）+ 混合会话结算
- 子系统 4 后端：Question.in_practice_pool 字段 + PUT /api/questions/{id} 编辑（按题型校验）+
  DELETE /api/questions/{id} 删除（清理引用会话 question_ids）+ POST /api/questions/{id}/publish
  确认进池 + GET /api/documents/{id}/questions/drafts 草稿预览 + generate-quiz auto_publish 参数
  （默认 True 生成即进池，保留 1.1 闭环；False 生成草稿待确认）
- 子系统 6 后端：完整 6 维自评（accuracy/clarity/difficulty/source_grounding/
  non_trivial/non_ambiguous）+ 向后兼容部分维度 + 可配阈值（默认 2/3 等价总分 4）+
  self_eval_scores 明细（内存）

前端 Settings UI、运行时出题/答题改用 DB 配置、交叉出题前端——均待后续轮次。

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

### 2026-06-24 轮次 4：完整 6 维自我批评管线（子系统 6）

TDD（先红后绿），5 个新测试（1 prompts + 4 generator + 1 api），累计 136 全绿。一个 commit。

**自评维度扩展（`services/quiz/prompts.py` `build_eval_messages`）**
- 从 2 维（accuracy + source_grounding）扩展到完整 6 维（对齐 PRD 子系统 6）：
  accuracy / clarity / difficulty / source_grounding / non_trivial / non_ambiguous
- prompt 要求 LLM 返回 6 个 0-1 浮点；user message 增补「标注难度」供 difficulty 维度比对
- difficulty 字段用 getattr 安全访问，兼容不含该属性的 duck-typed question（测试用 SimpleNamespace）

**6 维分数计算（`services/quiz/generator.py`，纯逻辑）**
- 新增 `SELF_EVAL_DIMENSIONS` 常量 + `_compute_self_eval_score(data) -> (score, scores)`：
  对返回中**实际存在**的维度取平均 → 向后兼容旧 2 维 mock 响应（EVAL_HIGH 仍 0.9，不破坏现有测试）
- 一个有效维度都没有 → (None, None)，调用方保守保留题目不打分（不因自评抖动丢弃已生成内容）
- `GeneratedQuestion` 加 `self_eval_scores: dict | None`（各维度明细，仅生成期内存，不落库）
- 默认阈值 0.6 → 2/3（≈0.667），等价 6 维总分 4 淘汰（对齐 PRD「默认 <4 分淘汰」）
- generate_quiz 自评块改用 _compute_self_eval_score + 记录 scores；简答仍跳过生成期自评

**可配阈值（`schemas/quiz.py` + `routers/quiz.py`）**
- `QuizGenerationRequest` 加 `self_eval_threshold: float | None`（None=用默认 2/3）
- **语义区分修复（关键，ASGITransport 测试发现）**：schema 的 None=「用默认」与 generate_quiz 的
  None=「跳过自评」冲突；router 直接透传 None 会让默认出题跳过自评 → self_eval_score=None。
  修复：router 条件传参——未指定时不传（用 generate_quiz 默认 2/3 启用自评），用户显式传值时覆盖
  （0=保留全部题不淘汰但仍自评记分，调高则更严格淘汰）

**测试**：test_quiz_prompts（替换 2 维断言为 6 维）/ test_quiz_generator（+4：6 维保留+scores 明细 /
6 维淘汰 / 部分维度向后兼容 / 默认阈值淘汰）/ test_quiz_api（+1：self_eval_threshold 可配）

### 2026-06-24 轮次 5：交叉出题 + 标记坏题后端（子系统 5）

TDD（先红后绿），15 个新测试（6 interleave + 1 quiz_api 交叉端到端 + 8 questions_api），
累计 151 全绿。一个 commit。

**交叉出题纯逻辑（`services/quiz/generator.py` `interleave_questions`，新纯函数）**
- 以 concept_index 为主分组做 round-robin 轮转：每轮从各非空组各取一题，相邻两题自然来自不同 concept
  （最大组题数 <= 其余组之和 + 1 即"可调度"时相邻全不同；超出属数学极限）
- 组内按 (question_type, 原序) 稳定排序使题型也尽量打散
- 不改变题目集合，仅重排；结果稳定（同一输入恒定输出），便于测试与可重现

**交叉出题接入（`routers/quiz.py`）**
- generate_quiz_for_document 落库前对 gen.questions 交错（默认开启）
- question_orm 落库顺序 + QuizSession.question_ids + 响应 questions 均为交错后顺序
- 不影响 concept 落库顺序（concept 无需交错）；单题场景交错为自身，现有测试零破坏

**标记坏题数据模型（`models/quiz.py`）**
- Question 加 `is_flagged: bool`（默认 False，nullable=False）

**标记坏题 API（`routers/questions.py`，新文件，prefix /api/questions）**
- POST /{question_id}/flag：is_flagged=True（幂等，重复标记仍 True）
- DELETE /{question_id}/flag：is_flagged=False（取消，重回练习池）
- 标记不影响已生成的答题会话（Question 仍存 DB，已含它的 QuizSession 照常可答）

**练习池列表（`routers/quiz.py` GET /{document_id}/questions）**
- 返回 QuestionOut 列表，排除 is_flagged=True（"移出 practice pool" 的可测行为）
- QuestionOut 暴露 is_flagged 字段（前端据此隐藏/禁用坏题）
- 子系统4 预览编辑的列表基础；本轮只读（编辑/删除/确认进池留子系统4）

**测试**：test_interleave（6 新文件：空/单题/2×2 交叉/3-2-1 不均衡/集合长度保持/确定性）/
test_quiz_api（+1：多 concept 多题端到端交错，相邻 concept 不同 + question_ids 与响应一致）/
test_questions_api（8 新文件：flag 落库+幂等/unflag/404/练习池排除 flagged/练习池仅返回 unflagged/
未知文档 404/全标记空列表）

**未做（明确留后续）**：
- 前端答题界面"标记坏题"按钮 + 交叉出题顺序的前端展示（前端轮次，需 yufeng 浏览器验证）
- "移出 practice pool" 的完整语义随子系统4（预览编辑确认进池）+ 错题复习（Phase 2）落地：
  当前每次出题新生成题（不复用已存题），标记的排除体现在练习池列表查询；未来从已存题复用出题
  （错题变体/复习）时排除 is_flagged=True 的题

### 2026-06-24 轮次 6：题目预览编辑后端核心（子系统 4）

TDD（先红后绿），15 个新测试（11 编辑/删除/publish/草稿 + 2 未知 404 + 2 端到端 generate 草稿），
累计 166 全绿。一个 commit。

**数据模型扩展（`models/quiz.py`）**
- `Question.in_practice_pool: bool`（默认 True，nullable=False）
  - False=草稿（生成后待预览/编辑/确认），True=已进练习池（GET 练习池列表可见）
  - 与子系统5 is_flagged 正交：flagged=坏题移出池，draft=未确认进池；GET 练习池两者皆排除

**出题引擎扩展（`routers/quiz.py`）**
- `generate_quiz_for_document` 落库 Question 时设 `in_practice_pool=params.auto_publish`
  - 默认 auto_publish=True（保留切片 1.1 生成→可答闭环：生成即进池、QuizSession 立即可答）
  - auto_publish=False 生成草稿题，需预览编辑后 POST /publish 确认进池
- `QuizGenerationRequest.auto_publish: bool = True`
- `list_practice_pool_questions` 过滤加 `in_practice_pool.is_(True)`（草稿不返回，保留 is_flagged 排除）
- 新增 `GET /api/documents/{id}/questions/drafts`：返回草稿题（in_practice_pool=False，排除 flagged）

**编辑/删除/确认路由（`routers/questions.py`）**
- `PUT /api/questions/{id}`：部分更新（None 字段保留原值）；按题型校验编辑后合法性
  - 选择题：options 非空 + correct_option_index 在范围内（不合法 → 422）
  - 简答题：answer_text 非空白（空 → 422）
  - 404 题不存在
- `DELETE /api/questions/{id}`：删题 + 清理引用它的 QuizSession.question_ids（JSON 列表移除该 id）
  - Answer 表 question_id 有 ondelete=CASCADE 级联删；question_ids 是 JSON 非外键需手动移除
  - 避免进行中会话结算时 set(quiz.question_ids) 残留已删题 id 永不可答
  - 404 题不存在；返回 204 No Content
- `POST /api/questions/{id}/publish`：确认进池（in_practice_pool=True），幂等

**Schema（`schemas/quiz.py`）**
- `QuestionOut` 加 `in_practice_pool: bool`
- 新增 `QuestionUpdateRequest`（stem/options/correct_option_index/answer_text/explanation 全可选）

**测试**：test_questions_preview_api（15 新文件）：编辑选择题 stem/options/correct + 部分更新保留 +
编辑简答 answer_text + correct 越界 422 + 简答空 answer_text 422 + 编辑 404 +
删除落库 + 删除 404 + 删除清理引用会话 question_ids（全新 session 读 DB 真实值，绕过 identity map）+
publish 落库+幂等 + publish 404 + 草稿列表排除已进池 + 草稿 404 + 端到端 generate auto_publish=False→
drafts 可见/练习池不可见→publish→练习池可见 + 默认 auto_publish=True 生成即进池

**真机冒烟未做（判断）**：子系统4 = DB CRUD（PUT/DELETE/publish/drafts 不调 LLM、不构造外部 client）+
generate-quiz 仅加 in_practice_pool 落库（LLM 路径不变，端到端用 llm_mock 进程内 client 无外部 httpx
构造盲区）。ASGITransport 测试已覆盖路由语义/落库/JSON 列清理/端到端草稿闭环。故未做 uvicorn 冒烟，
避免重复本机 SOCKS 代理干扰。

### 2026-06-24 轮次 7：运行时改用 DB 配置（子系统1 后端收口增量）

TDD（先红后绿），8 个新测试（4 resolve 纯逻辑 + 2 get_llm_client 依赖 + 2 路由集成），累计 174 全绿。
一个 commit。子系统1 后端闭环的最后一块：之前 Settings 页保存的 DB 配置只能存 / 读脱敏视图，
运行时出题/答题仍走 env（`get_llm_client` 直接 `make_llm_client(get_settings())`）。本增量让
`get_llm_client` 优先读 DB settings，未配置或读取失败回退 env——用户配置后无需重启即生效。

**解析逻辑层（`dependencies.py` `resolve_llm_settings`，新纯异步函数）**
- `resolve_llm_settings(session, settings) -> Settings`：优先读 DB 配置（`load_llm_config`），
  返回 `settings.model_copy(update={4 个 llm 字段})`；未配置 / 读取异常（secret 缺失或解密失败）
  → 回退原 env settings（保守降级，不阻断出题）
- DB 配置 model 为空 → 用 env 的 model 兜底（`db_config.model or settings.llm_model`）
- 用 `model_copy(update=...)` 而非新建 `Settings(...)`：保留 secret_key 等其他字段，不重读 env

**依赖层（`dependencies.py` `get_llm_client`，sync → async generator）**
- `def get_llm_client() -> LLMClient` → `async def get_llm_client(session=Depends(get_session))
  -> AsyncIterator[LLMClient]`：复用请求级 session（FastAPI sub-dependency 去重，同请求共享），
  `resolved = await resolve_llm_settings(session, get_settings())` → `yield make_llm_client(resolved)`
- **DB 配置已解密但 make_llm_client 构造失败不兜底**：如 openai 在缺 socksio 的代理环境
  AsyncOpenAI 构造抛 ImportError——让错误上浮（路由 500），**不静默降级到 mock**（避免用户配了
  openai 却默默用 mock 出错题）。回退 env 仅在「DB 读不到 / 解密失败」时发生（DB 不可信才回退）
- **关键探针验证**：把 sync 依赖改 async-gen 后，现有 `llm_mock` fixture 的
  `app.dependency_overrides[get_llm_client] = lambda: mock`（sync 返回值）是否仍兼容？
  写最小 FastAPI 探针确认 FastAPI 0.138.0 下 sync-value override 对 async-gen 依赖有效——
  override 完全替换 callable，FastAPI 按 override 类型处理，与原签名无关。故 166 现有测零破坏。

**测试**：test_llm_runtime_config（8 新文件）：
- resolve 纯逻辑×4：DB 配置→DB 字段 / 未配置→env 不变 / 解密失败→env / DB model 空→env model 兜底
- get_llm_client 依赖×2：monkeypatch make_llm_client 为记录器，DB 配置→captured model=db-special
  （非 env gpt-4o）；未配置→captured model=gpt-4o（env）。async gen 用 `__anext__` + `aclose` 正确收尾
- 路由集成×2：**不请求 llm_mock**（不 override get_llm_client），让真实 async-gen 经 Depends 在
  generate-quiz 路由解析——证明接线 + DB 配置生效（captured.llm_model==db-special）；
  未配置→env（gpt-4o）。这是关键：现有所有 quiz/answer 测试都 override get_llm_client，
  **无任何测试覆盖真实 get_llm_client**，改 async-gen 后必须有路由级测试证明 Depends 接线未坏
  （同 review notes「ASGITransport 掩盖真机问题」教训——ASGITransport 路由测能抓依赖解析 bug）

**未做（明确留后续）**：前端 Settings 页（写 DB 配置的 UI，需 yufeng 浏览器验证）；简答异步轮询
（需真实 LLM）。openai DB 配置在 SOCKS 代理环境的 AsyncOpenAI 构造失败 → 路由 500（不静默降级），
属部署环境 blocker（同切片 1.1 SOCKS blocker，真实部署装 httpx[socks] 或清代理）。

## 子系统进度（按 SLICE_PHASE_1.md 切片 1.2 任务清单）

- [~] 1. LLM 配置 UI 与后端（Settings 页 + provider/key/model/base_url 存 SQLite settings 表 + POST /api/settings/llm + 测试调用连通验证）
  - [x] 后端：加密存储 + KV 表 + GET/POST API + 连通测试 —— 轮次 1
  - [x] 运行时出题/答题改用 DB 配置（get_llm_client 读 settings 表，fallback env）—— 轮次 7
  - [ ] 前端 Settings 页（provider 选择 + key 输入 + model/base_url + 测试按钮）—— blocker（浏览器）
- [ ] 2. 出题参数控制（number/difficulty_range/question_types/chapter_scope/bloom_distribution API + 前端面板 + Bloom 完整 4 层）
  - [x] 后端：参数 schema + generate_quiz 扩展 + prompt Bloom 四层 + POST body + 测试 —— 轮次 2
  - [ ] 前端出题配置面板（选择题数/难度/题型比例/章节范围）
  - [ ] 真正多题型生成（true_false/fill_blank/short_answer，留子系统 3 配套评分）
- [ ] 3. 简答题生成与评分（short_answer 题型 + LLM rubric 评分 + 异步轮询）
  - [x] 后端：short_answer 题型生成 + LLM rubric 评分 0-1 + 引用文档反馈 + Answer 按题型分流 + 混合会话结算 —— 轮次 3
  - [ ] 异步评分 + 前端轮询（同步评分已通，异步状态机留真实 LLM 接入后）
- [~] 4. 题目预览与编辑（预览模式 + 编辑/删除 + 确认进练习池）
  - [x] 后端：in_practice_pool 字段 + PUT 编辑（按题型校验）+ DELETE 删除（清理引用会话）+
    POST publish 确认进池 + GET /drafts 草稿预览 + auto_publish 参数 —— 轮次 6
  - [ ] 前端预览编辑界面（列表 + 编辑表单 + 删除按钮 + 确认进池）
- [x] 5. 交叉出题 + 标记坏题（按 concept 交叉混合 + 坏题移出 practice pool） —— 轮次 5
  - [x] 后端：interleave_questions 纯函数（round-robin by concept）+ router 落库前交错 +
    Question.is_flagged 字段 + POST/DELETE /api/questions/{id}/flag + GET /api/documents/{id}/questions
    练习池列表（排除 flagged）+ QuestionOut.is_flagged
  - [ ] 前端答题界面"标记坏题"按钮 + 交叉顺序展示（前端轮次）
- [x] 6. 完整自我批评管线（6 维度自评 + 可配淘汰阈值） —— 轮次 4

## 验收标准核对

- [ ] Web UI Settings 页配置 LLM provider + API key 后，测试调用成功 —— 后端 API + 连通测试已通；前端 UI 待
- [ ] 出题时可选择题型/难度/数量/章节范围 —— 子系统 2 后端已通；前端面板待
- [x] 简答题提交后 LLM 评分返回 0-1 + 引用文档解释 —— 子系统 3 后端（同步评分；异步轮询留后续）
- [~] 题目生成后可预览/编辑/删除，确认后进练习池 —— 子系统 4 后端（auto_publish=False 草稿→编辑/删除→
  publish 进池完整闭环；auto_publish=True 默认生成即进池保留 1.1 闭环）；前端预览编辑 UI 待
- [x] 答题时题目顺序交叉混合 —— 子系统 5（轮次 5，按 concept round-robin 交错，相邻题不同 concept）
- [x] 可标记坏题 —— 子系统 5（轮次 5，is_flagged + flag/unflag API + 练习池列表排除）
- [x] 完整 6 维度自评 + 可配阈值 —— 子系统 6（轮次 4）

## 还剩

切片 1.2 子系统 1-6 后端全部完成（含子系统1 运行时 DB 配置收口），**可运行后端工作已耗尽**。
剩余全是 blocker（非 agent 可推进）：
- 前端轮次（Settings 页 / 出题配置面板 / 预览编辑 / 标记坏题 UI）—— 需 yufeng 浏览器验证
- 子系统 3 异步评分轮询 —— 需真实 LLM（同步评分已通）

下一轮若 monitor 判定 1.2 后端完成 → 推进切片 1.3（闪卡 FSRS，依赖 1.1+1.2 已满足）。

## Blockers

- **真实 LLM key**：连通测试的 openai provider 真实路径需真实 key + 网络。本机 SOCKS 代理环境
  `AsyncOpenAI` 构造缺 socksio 会失败——已优雅降级为 ok=False + message（非 500），真实部署需 yufeng
  注意装 `httpx[socks]` 或清代理（同切片 1.1 blocker）。真实连通质量 + 简答 rubric 评分质量
  待 yufeng 真实 key 验证。**运行时 DB 配置为 openai 时同理**：AsyncOpenAI 构造失败 → 路由 500
  （不静默降级到 mock，避免用错配置出题），真实部署同需 socksio/清代理。
- **QUIZCRAFT_SECRET_KEY 部署**：加密 API key 需配置 secret。未配置时含 key 的配置被 400 拒绝（保护性）；
  运行时 `resolve_llm_settings` 读 DB 配置时 secret 缺失 → 解密失败 → 回退 env（不阻断出题，但 DB openai
  配置不生效）。mock provider 无 key 不受影响。自部署务必配置（生产安全基线）。
- **运行时 LLM 配置来源**：~~需改 get_llm_client 依赖为 async 读 DB~~ —— 轮次 7 已完成。
  get_llm_client 现为 async generator，优先读 DB settings（fallback env）；用户配置后无需重启即生效。
- **异步简答评分轮询**：本轮同步评分（提交即返回 score+feedback）。真实 LLM 评分耗时数秒到数十秒，
  同步会阻塞 HTTP。异步状态机（Answer pending→scored）+ 轮询端点留真实 LLM 接入后再做。
- **前端浏览器人机交互**：无 Playwright 自动化，Settings 页/简答作答/标记坏题 UI 待 yufeng
  `cd frontend && npm run dev` 实地验证。
- **is_flagged / in_practice_pool 新字段真机 DB 迁移**：轮次5 给 questions 表加 is_flagged 列，
  轮次6 加 in_practice_pool 列。测试用内存 SQLite（conftest create_all 每次新建，含新列）不受影响；
  但真机 dev DB 文件若已存在（前轮 create_all 建的旧 questions 表无此两列），lifespan create_all
  只 CREATE TABLE IF NOT EXISTS 不 ALTER 加列 → flag/practice-pool/edit/delete/publish/drafts 端点
  命中无列报错。真机需删 dev DB 文件重建（create_all 单机原型限制，生产换 Alembic 迁移，同切片 1.1 blocker）。
- **真机冒烟未做（判断）**：轮次7 = DB 读 + model_copy（纯逻辑，不构造外部 client）+ async-gen 依赖接线
  （ASGITransport 路由集成测试已覆盖真实 get_llm_client 经 Depends 解析）。无轮次1/3 的 AsyncOpenAI
  构造期副作用盲区（测试用 mock DB 配置）。故未做 uvicorn 真机冒烟，避免重复本机 SOCKS 代理干扰。
