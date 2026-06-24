# QuizCraft Ralph 循环总进度

> 全局进度索引。每轮 Codex Ralph 读写本文件顶部。状态活在 git commit + issue progress 文件，不靠对话记忆。
> 当前调度顺序：`docs/agents/tdd-issue-split.md` 的 TDD 行为切片队列 #16-#38。

## 当前状态

**STATUS: IN PROGRESS**

- 当前队列：GitHub TDD issues #16-#38；旧功能桶 issues #5-#15 已 superseded。
- 本轮推进：#20 `[TDD 2A] Flashcards from concepts and wrong answers`
  错题提交后自动生成 source-linked elevated flashcard，`GET /api/flashcards`
  支持按 document/concept 列表查询。
- 当前可领取：#20 仍 `IN PROGRESS`；本轮未修改 GitHub issue/label/PR。
- 下一步：继续 #20 的下一个最小行为增量：概念闪卡创建与去重，或补错题类型覆盖后再进入列表 UI。
- 监控节奏：Codex heartbeat 每 20 分钟检查一次；同一 worktree 只允许一个 Ralph runner 写代码。

## 切片完成情况

| 切片 | 状态 | progress 文件 | 备注 |
|------|------|---------------|------|
| 1.1 最小出题闭环 | COMPLETE | docs/progress/SLICE_1_1.md | 6 子系统全完成，后端 71 测 + 前端 21 测绿；真实 LLM/真实 PDF fixture 待 yufeng |
| 1.2 后端能力存量 | PARTIAL | docs/progress/SLICE_1_2.md | 作为 #16-#19 的后端基础使用；不再作为当前执行队列 |
| #16 Draft question review loop | COMPLETE | docs/progress/ISSUE_16.md | 前端草稿审核流 + 后端 draft APIs 验证完成 |
| #17 Quiz generation controls UI | COMPLETE | docs/progress/ISSUE_17.md | 前端 generation controls + 参数请求行为完成 |
| #18 Mixed question answering loop | COMPLETE | docs/progress/ISSUE_18.md | 前端混合题型答题和结果汇总完成 |
| #19 LLM settings UI/runtime smoke | COMPLETE | docs/progress/ISSUE_19.md | Settings UI + runtime smoke 验证完成 |
| #20 Flashcards from concepts and wrong answers | IN PROGRESS | docs/progress/ISSUE_20.md | 错题 source-linked elevated flashcard + 列表 API 完成；概念闪卡/去重/UI 待后续 |
| #21-#38 | 未开始/阻塞 | docs/progress/ISSUE_<n>.md | 依赖前序 TDD issue |

## 已完成总览

### 切片 1.1（6 子系统，6 轮）

1. 后端骨架：FastAPI + async SQLAlchemy 模型（Document/Section/Concept/Question/QuizSession/Answer）+ LLM 抽象层（MockLLMClient/OpenAICompatibleClient/工厂）+ 配置（`QUIZCRAFT_` 环境变量）
2. 文档解析：PyMuPDF4LLM 经典路径 + 结构感知分块（header 栈 section_path，512-1024 token，三级回退）+ POST/GET /api/documents
3. 出题引擎：两步生成（Step1 Concepts / Step2 选择题）+ 简化自评（accuracy+source-grounding）+ POST /api/documents/{id}/generate-quiz
4. 答题反馈：POST /api/quiz-sessions/{id}/answer + 确定性判分 + LLM 引用原文反馈（空响应兜底）+ 会话结算
5. 前端：Next.js 15 App Router + 上传/答题/错题反馈单页 + CORS + lifespan 建表（真机冒烟发现的 bug 修复）
6. 端到端集成测试：上传→出题→答题→反馈全链路（source_span 从真实解析贯穿到用户可见反馈，双路径：LLM 有响应 / LLM 空兜底）

### 切片 1.2 子系统 1（轮次 1）

- LLM 配置后端核心：API key Fernet 加密（cryptography，secret 从 QUIZCRAFT_SECRET_KEY 派生）+ KV settings 表 +
  GET/POST /api/settings/llm（脱敏读 + 加密写 + 立即连通测试）。真机冒烟发现 check_llm_connection 构造期
  ImportError 逃逸 → 500（SOCKS 代理环境），修复为 except Exception 全捕获降级 ok=False。

### 切片 1.2 子系统 2（轮次 2）

- 出题参数控制后端：`QuizGenerationRequest`（number / difficulty_range / question_types /
  chapter_scope / bloom_distribution）+ `generate_quiz` 扩展（difficulty 过滤、number 截断）+
  `filter_sections_by_scope` 纯函数（section_path 子串白名单）+ Bloom 完整四层（记忆/理解/应用/分析，
  原仅记忆/理解）+ POST /api/documents/{id}/generate-quiz 接受可选 body（无 body 退回切片 1.1 默认）。
  question_types 当前仅 multiple_choice（多题型生成与评分方式绑定，留子系统 3 简答评分配套）。

### 切片 1.2 子系统 3（轮次 3）

- 简答评分后端：`QuestionType.SHORT_ANSWER` + Question 加 `answer_text`（参考答案/rubric）+
  `correct_option_index` 可空 + Answer 加 `short_answer_text`/`score`；`generate_quiz` 按 question_types
  分支生成简答题（`build_step2_short_answer_messages`）；`score_short_answer` 纯逻辑层（LLM rubric 评 0-1，
  clamp + 兜底锚定来源）；`submit_answer` 按题型分流（选择确定性判分 / 简答 LLM 评分）；混合会话结算
  `score=(选择题正确数+简答分数和)/总题数`；幂等 upsert 五字段。同步评分（异步轮询留真实 LLM 接入后）。

### 切片 1.2 子系统 6（轮次 4）

- 完整 6 维自评后端：`build_eval_messages` 扩展 accuracy/clarity/difficulty/source_grounding/
  non_trivial/non_ambiguous 六维；`_compute_self_eval_score` 对存在维度取平均（向后兼容旧 2 维 mock）；
  默认阈值 0.6→2/3（等价总分 4，对齐 PRD「默认 <4 分淘汰」）；`GeneratedQuestion.self_eval_scores` 记
  各维度明细（内存不落库）；`QuizGenerationRequest.self_eval_threshold` 可配 + router 条件传参
  （区分 schema None=用默认 vs generate_quiz None=跳过自评，避免默认出题静默跳过自评）。

### 切片 1.2 子系统 5（轮次 5）

- 交叉出题 + 标记坏题后端：`interleave_questions` 纯函数（concept round-robin 轮转，相邻题不同 concept，
  组内按 question_type 打散，稳定可重现）+ router 落库前交错（question_ids/响应均为交错顺序，单题零破坏）；
  `Question.is_flagged` 字段 + `routers/questions.py`（POST/DELETE /api/questions/{id}/flag 幂等）+
  `GET /api/documents/{id}/questions` 练习池列表（排除 is_flagged=True，"移出 practice pool" 可测行为）+
  QuestionOut.is_flagged。前端标记按钮/交叉展示留前端轮次。

### 切片 1.2 子系统 4（轮次 6）

- 题目预览编辑后端：`Question.in_practice_pool` 字段（默认 True 保留 1.1 生成即进池闭环，False 草稿待确认）+
  `PUT /api/questions/{id}` 编辑（部分更新 + 按题型校验：选择题 options/correct 范围、简答 answer_text 非空，不合法 422）+
  `DELETE /api/questions/{id}` 删除（清理引用它的 QuizSession.question_ids JSON 列表，Answer 级联删，204）+
  `POST /api/questions/{id}/publish` 确认进池（幂等）+ `GET /api/documents/{id}/questions/drafts` 草稿预览 +
  `generate-quiz` auto_publish 参数（True 进池 / False 草稿）。GET 练习池列表 now 排除草稿 + flagged。
  前端预览编辑界面留前端轮次。

### 切片 1.2 子系统 1 运行时 DB 配置（轮次 7）

- `get_llm_client` 由 sync 改 async generator（`Depends(get_session)` 复用请求级 session），
  优先 `resolve_llm_settings` 读 DB settings → `make_llm_client(resolved)`，未配置或解密失败回退 env。
  `resolve_llm_settings` 用 `settings.model_copy(update={4 个 llm 字段})` 保留 secret_key 等，
  DB model 空用 env 兜底。DB 配置已解密但 make_llm_client 构造失败（openai 在缺 socksio 代理环境）
  **不静默降级到 mock**——让错误上浮路由 500，避免用户配 openai 却默默用 mock 出错题。
- 探针验证 FastAPI 0.138.0 sync-value override 对 async-gen 依赖有效 → 现有 `llm_mock` fixture 零破坏。
- 路由集成测试覆盖真实 async-gen get_llm_client 经 Depends 解析（现有测试全 override，改签名后必须有
  路由级测试证明接线未坏，同「ASGITransport 掩盖真机」教训）。8 新测累计 174 全绿。

### TDD Issue #19（LLM settings UI/runtime smoke）

- 前端新增 `SettingsPanel`，在 QuizCraft 单页顶部提供 provider、model、API key、base URL 表单；
  保存后显示脱敏配置摘要（`has_api_key`）和连接检查结果。
- 前端 settings API client 覆盖 `GET /api/settings/llm` 与 `POST /api/settings/llm`，测试断言调用方不接收明文
  `api_key`，失败连接作为 `connection.ok=false` 数据返回。
- 后端 `POST /api/settings/llm` 修正省略 `api_key` 的语义：已有 key 不回显时，保存 model/base_url 不会意外清空
  已存密钥；显式传 null/空值仍可清空。
- 验证：前端 33 测、typecheck、build 通过；后端 200 测通过；Chrome headless 桌面/移动渲染无水平溢出，openai 无 key
  显示非致命黄色连接失败反馈。

### TDD Issue #20（Flashcards from concepts and wrong answers）

- 后端新增 `Flashcard` 模型与 `GET /api/flashcards` 列表接口，可按 `document_id` 或 `concept_id` 过滤。
- `POST /api/quiz-sessions/{id}/answer` 在错题或部分得分答案后创建一张 `origin=wrong_answer`、
  `priority=elevated`、带 `source_span` 的闪卡，front 使用原题题干，back 包含正确答案、来源原文和反馈。
- `source_answer_id` 唯一约束避免同一作答重复生成错题卡；FSRS 调度、概念卡创建、列表 UI 留后续增量。
- 验证：新闪卡 API 测试红灯为 404；实现后 `backend/tests/test_flashcards_api.py` 绿；相关答题测试 22 绿；
  后端全量 201 绿。

## Blockers（跨切片，待 yufeng 外部资源）

- **真实 LLM key**：全部 LLM 调用用 MockLLMClient 覆盖；真实出题/反馈质量、Bloom 分布、干扰项是否真基于常见误解待 yufeng 真实 key 验证。运行时 DB 配置为 openai 时 AsyncOpenAI 构造失败同切片 1.1 SOCKS blocker。
- **真实 10-50 页课件 PDF fixture**（含复杂排版/扫描页）：解析质量待样本验证；L2/L3 分层路由在切片 1.4
- **前端浏览器人机交互**：无 Playwright 自动化，待 yufeng `cd frontend && npm run dev` 实地验证
- **SOCKS 代理环境**：openai SDK 构造 AsyncOpenAI 在带 SOCKS 代理的本机缺 socksio 会失败（测试已 monkeypatch 规避），真实部署需注意
- **生产部署建表**：切片 1.1 用 `create_all`（单机原型），生产换 Alembic 迁移待 yufeng 决策（切片 1.5）
- **ruff 离线不可用**：本机无 ruff 二进制，`uvx ruff` 因 pypi 网络超时下载失败。本轮手动按 ruff 风格
  审查超长行（已确保无新引入的函数调用超长行；剩余超长行均为 docstring/注释/字符串字面量，ruff format
  不拆，与原代码一致）。monitor 复跑 `uvx ruff format --check backend` 若失败多为网络问题非代码问题；
  yufeng 可在有网环境 `uv tool install ruff` 后复验。
- **is_flagged / in_practice_pool 新字段真机 DB 迁移**：轮次5/6 给 questions 表加列。测试内存 DB 不受影响；
  真机 dev DB 文件若已存在，create_all 不 ALTER 加列 → 端点报错，需删库重建（同 create_all 单机限制）。

## 约定

- 不 push、不发 PR、不改 GitHub issue、不用 gh —— 只本地 commit
- 只提交产品代码、测试、docs/progress；不提交 `.codex-loop/`、缓存、node_modules、构建产物
- 每轮一个有意义增量（一个子系统核心 + 测试），不贪完整个大 Phase
- TDD：先红后绿再重构，无测试不提交
