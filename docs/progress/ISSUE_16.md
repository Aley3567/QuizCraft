STATUS: COMPLETE

# ISSUE #16 - Draft question review loop before practice

## 本轮完成

- 领取最小编号 claimable issue：`gh#16 [TDD 1B] Draft question review loop before practice`。
- 读取本地 queue、TDD issue split、agent readiness、triage labels、issue tracker、PRD Phase 1、Slice Phase 1、相关源码/测试、近期 git log、Ralph review notes。
- `gh issue view 16 --json title,body,labels` 被仓库 Ralph guard 拦截：`Blocked by QuizCraft Ralph loop guard: GitHub CLI operations are not allowed.` 使用 `.codex-loop/issues.raw.json` 的本地 GitHub 快照读取完整 issue body。
- TDD 红测：新增前端 public API 测试，先失败于缺失 `generateDraftQuiz` / `listDraftQuestions` / `updateQuestion` / `publishQuestion` / `deleteQuestion`。
- 最小绿码：
  - 前端 API 增加 draft review 相关公共封装：`auto_publish=false` 生成草稿、读取草稿、读取练习池、编辑、删除、发布。
  - 前端类型对齐后端 `QuestionOut` / `AnswerOut`：支持 `answer_text`、`is_flagged`、`in_practice_pool`、可空 `correct_option_index`、简答评分字段。
  - 新增 `DraftReview` 组件：展示草稿题题型、来源引用、原文片段；可编辑题干/选择题选项/正确答案下标/简答参考答案/解析；可删除或发布。
  - 主页流程由“生成后直接答题”改为“生成草稿题 -> 审核草稿 -> 发布后开始练习”。

## 验收项

- [x] Draft generation keeps questions out of the practice pool.
  - 前端 `generateDraftQuiz` 固定发送 `{ "auto_publish": false }`；后端既有 `test_generate_draft_then_publish_into_pool` 覆盖草稿不进练习池。
- [x] Draft list shows source citation and question type.
  - `DraftReview` 显示 question type tag、Bloom/difficulty tag、`formatSourceSpan` 和 `sourceExcerpt`。
- [x] Editing a draft persists changed text and answer fields.
  - 前端 `updateQuestion` 走 `PUT /api/questions/{id}`；后端既有编辑测试覆盖题干、选项、正确答案、简答参考答案。
- [x] Deleting a draft removes it from draft and practice queries.
  - 前端 `deleteQuestion` 走 `DELETE /api/questions/{id}`；后端既有删除测试覆盖 DB 删除和 session 引用清理。
- [x] Publishing a draft makes it available in practice.
  - 前端 `publishQuestion` 走 `POST /api/questions/{id}/publish`，发布后进入本地可练习题集合；后端既有测试覆盖练习池可见。
- [x] Verification exercises public APIs or browser-visible behavior, not private helpers.
  - 新测试 mock 浏览器 `fetch` 边界并断言公开 API 路径/请求体；后端测试走 FastAPI public routes。

## 验证

- RED: `cd frontend && npm test -- --run`
  - 预期失败：5 个 draft review API 测试失败于缺失函数导出。
- GREEN: `cd frontend && npm test -- --run`
  - 结果：2 files passed, 26 tests passed。
- `cd frontend && npm run typecheck`
  - 结果：通过，`next typegen && tsc --noEmit`。
- `uv run pytest backend/tests/test_questions_preview_api.py`
  - 结果：15 passed, 7 warnings。
- `cd frontend && npm run build`
  - 结果：Next.js production build 通过。
- `uv run pytest backend`
  - 结果：199 passed, 7 warnings。

## 剩余/Blocker

- #16 本地行为完成。
- 未做真实浏览器人工点击验证；本轮以 frontend build/typecheck + public API tests + backend route tests 作为可重复验证。
- 既有跨切片 blocker 仍存在：旧本地 SQLite dev DB 若缺 `is_flagged` / `in_practice_pool` 列，`create_all` 不会迁移旧表，需要删库重建或后续引入 Alembic。
