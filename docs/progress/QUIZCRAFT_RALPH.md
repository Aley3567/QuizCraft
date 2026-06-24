# QuizCraft Ralph 循环总进度

> 全局进度索引。每轮 Ralph 读写本文件顶部。状态活在 git commit + 各切片 progress 文件，不靠对话记忆。
> 调度顺序：Phase 1 (1.1→1.5) → Phase 2 (2.1→2.5) → Phase 3 issue #5-#9 → Phase 4 issue #10-#15。

## 当前状态

**STATUS: IN PROGRESS**

- 当前切片：**Phase 1 切片 1.2（LLM 配置与出题增强）** —— 下一轮开始
- 上一轮完成：切片 1.1 子系统 6（端到端集成测试），切片 1.1 STATUS: COMPLETE
- 下一步：切片 1.2 第一个子系统「LLM 配置 UI 与后端」（Settings 页 + provider/key/model/base_url 存 SQLite settings 表 + POST /api/settings/llm + 测试调用连通验证）

## 切片完成情况

| 切片 | 状态 | progress 文件 | 备注 |
|------|------|---------------|------|
| 1.1 最小出题闭环 | COMPLETE | docs/progress/SLICE_1_1.md | 6 子系统全完成，后端 71 测 + 前端 21 测绿；真实 LLM/真实 PDF fixture 待 yufeng |
| 1.2 LLM 配置与出题增强 | 未开始 | — | 依赖 1.1（已满足） |
| 1.3 闪卡与 FSRS | 未开始 | — | 依赖 1.1+1.2 |
| 1.4 DOCX 与分层解析 | 未开始 | — | 依赖 1.1+1.2 |
| 1.5 自部署与离线 | 未开始 | — | 依赖 1.1-1.4 |
| 2.1-2.5 | 未开始 | — | 依赖 Phase 1 |
| 3.1-3.5 (issue #5-#9) | 未开始 | — | 依赖 Phase 1+2 |
| 4.1-4.6 (issue #10-#15) | 未开始 | — | 依赖 Phase 1-3 |

## 已完成总览

### 切片 1.1（6 子系统，6 轮）

1. 后端骨架：FastAPI + async SQLAlchemy 模型（Document/Section/Concept/Question/QuizSession/Answer）+ LLM 抽象层（MockLLMClient/OpenAICompatibleClient/工厂）+ 配置（`QUIZCRAFT_` 环境变量）
2. 文档解析：PyMuPDF4LLM 经典路径 + 结构感知分块（header 栈 section_path，512-1024 token，三级回退）+ POST/GET /api/documents
3. 出题引擎：两步生成（Step1 Concepts / Step2 选择题）+ 简化自评（accuracy+source-grounding）+ POST /api/documents/{id}/generate-quiz
4. 答题反馈：POST /api/quiz-sessions/{id}/answer + 确定性判分 + LLM 引用原文反馈（空响应兜底）+ 会话结算
5. 前端：Next.js 15 App Router + 上传/答题/错题反馈单页 + CORS + lifespan 建表（真机冒烟发现的 bug 修复）
6. 端到端集成测试：上传→出题→答题→反馈全链路（source_span 从真实解析贯穿到用户可见反馈，双路径：LLM 有响应 / LLM 空兜底）

## Blockers（跨切片，待 yufeng 外部资源）

- **真实 LLM key**：全部 LLM 调用用 MockLLMClient 覆盖；真实出题/反馈质量、Bloom 分布、干扰项是否真基于常见误解待 yufeng 真实 key 验证
- **真实 10-50 页课件 PDF fixture**（含复杂排版/扫描页）：解析质量待样本验证；L2/L3 分层路由在切片 1.4
- **前端浏览器人机交互**：无 Playwright 自动化，待 yufeng `cd frontend && npm run dev` 实地验证
- **SOCKS 代理环境**：openai SDK 构造 AsyncOpenAI 在带 SOCKS 代理的本机缺 socksio 会失败（测试已 monkeypatch 规避），真实部署需注意
- **生产部署建表**：切片 1.1 用 `create_all`（单机原型），生产换 Alembic 迁移待 yufeng 决策（切片 1.5）

## 约定

- 不 push、不发 PR、不改 GitHub issue、不用 gh —— 只本地 commit
- 只提交产品代码、测试、docs/progress；不提交 `.codex-loop/`、缓存、node_modules、构建产物
- 每轮一个有意义增量（一个子系统核心 + 测试），不贪完整个大 Phase
- TDD：先红后绿再重构，无测试不提交
