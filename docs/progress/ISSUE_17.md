STATUS: COMPLETE

# ISSUE #17 - Quiz generation controls in the UI

## 本轮完成

- 领取最小编号 claimable issue：`gh#17 [TDD 1C] Quiz generation controls in the UI`。
- 读取本地 queue、TDD issue split、agent readiness、triage labels、issue tracker、issue body、PRD Phase 1、Slice Phase 1、相关源码/测试、近期 git log、Ralph review notes。
- TDD 红测：新增前端 public API 测试，证明 `generateDraftQuiz(documentId, options)` 会把 `number`、`chapter_scope`、`difficulty_range`、`bloom_distribution` 连同 `auto_publish=false` 发送到 `POST /api/documents/{id}/generate-quiz`。
- 最小绿码：
  - 前端类型补齐 `QuizGenerationRequest` / `DraftQuizGenerationRequest`，对齐后端 `QuizGenerationRequest` schema。
  - `generateQuiz` 支持完整 generation 参数；`generateDraftQuiz` 支持传入参数并始终保留草稿语义 `auto_publish=false`。
  - 新增 `GenerationControls`：上传文档后可设置题数、章节范围、难度范围、Bloom 层级；Bloom 选择转成等权 `bloom_distribution`。
  - 主页上传后从单按钮生成改为“文档概览 + 生成设置”，提交后继续进入既有草稿审核流。
  - 对题数、难度、Bloom 空选择做前端提交前错误提示。

## 验收项

- [x] User can set question count.
  - `GenerationControls` 题数输入发送 `number`。
- [x] User can restrict generation by chapter or section scope.
  - 章节下拉来自 `doc.sections[].section_path`，发送 `chapter_scope`。
- [x] User can restrict difficulty range.
  - 难度复选框发送 `difficulty_range`。
- [x] User can select Bloom distribution or allowed Bloom levels.
  - Bloom 复选框发送等权 `bloom_distribution`。
- [x] Invalid combinations show a useful error before or after API submission.
  - 题数小于 1、难度为空、Bloom 为空均在前端提交前提示。
- [x] Tests verify the public request/response behavior.
  - 新增前端 fetch 边界测试验证请求体；既有后端 API/生成器测试覆盖 `number`、`chapter_scope`、`difficulty_range`、`bloom_distribution` 参数行为。

## 验证

- RED: `cd frontend && npm test -- --run src/lib/api.test.ts`
  - 预期失败：新测试收到的请求体只有 `{"auto_publish":false}`，缺少 generation controls 参数。
- GREEN: `cd frontend && npm test -- --run src/lib/api.test.ts`
  - 结果：1 file passed, 13 tests passed。
- `cd frontend && npm run typecheck`
  - 结果：通过，`next typegen && tsc --noEmit`。
- `cd frontend && npm test -- --run`
  - 结果：2 files passed, 27 tests passed。
- `uv run pytest backend/tests/test_quiz_api.py`
  - 结果：13 passed, 7 warnings。
- `cd frontend && npm run build`
  - 结果：Next.js production build 通过。

## 剩余/Blocker

- #17 本地行为完成。
- 未做真实浏览器人工点击验证；本轮以 frontend build/typecheck + public API tests + 后端 route tests 作为可重复验证。
