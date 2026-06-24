STATUS: COMPLETE

# ISSUE #18 - Mixed question answering loop

## 本轮完成

- 领取最小编号 claimable issue：`gh#18 [TDD 1D] Mixed question answering loop`。
- 读取本地 queue、TDD issue split、agent readiness、triage labels、issue tracker、issue body、PRD Phase 1、Slice Phase 1、相关源码/测试、近期 git log、Ralph review notes。
- TDD 红测：
  - 前端 `buildAnswerBody(8, { text: "类囊体膜" })` 先失败于把文本对象误当 `selected_option_index`。
  - 前端 `computeScore` 先失败于只按 `is_correct` 计数，未计入简答 `score` 部分分。
  - 前端 `wrongQuestions` 先失败于只筛 `is_correct=false`，未把简答未满分题放入反馈列表。
- 最小绿码：
  - `submitAnswer` / `buildAnswerBody` 支持选择题数字答案和填空/简答文本答案，文本答案发送 `short_answer_text`。
  - `QuizPlayer` 按 `question_type` 渲染选择题按钮、填空 input、简答 textarea；填空/简答提交文本答案并展示评分反馈。
  - `computeScore` 与后端混合会话规则对齐：选择题/填空按 `is_correct` 计 1，简答按 `score` 计部分分。
  - `wrongQuestions` 与 `ResultView` 支持简答未满分反馈，结果页显示得分制、文本作答、简答百分比分。

## 验收项

- [x] Fill-blank questions render an input and submit text answers.
  - `QuizPlayer` 对 `fill_blank` 渲染 input；`submitAnswer` 发送 `short_answer_text`。
- [x] Short-answer questions render a textarea and submit text answers.
  - `QuizPlayer` 对 `short_answer` 渲染 textarea；`submitAnswer` 发送 `short_answer_text`。
- [x] Multiple-choice behavior is preserved.
  - `submitAnswer(sessionId, questionId, number)` 继续发送 `selected_option_index`；选择题按钮逻辑保持原路径。
- [x] Mixed sessions compute one final score across all question types.
  - 前端 `computeScore` 计入简答部分分；后端 `test_answer_api.py` 继续覆盖混合会话结算。
- [x] Feedback includes source-grounded context where available.
  - `QuizPlayer` / `ResultView` 保留 source_span 页码、章节和原文片段展示；后端答题测试覆盖 source-grounded feedback。
- [x] Tests cover the behavior through API or rendered UI surfaces.
  - 前端 fetch 边界测试覆盖文本答案提交体；状态测试覆盖混合计分和未满分反馈；后端 public answer API 测试覆盖 mixed/fill_blank/short_answer。

## 验证

- RED: `cd frontend && npm test -- --run src/lib/api.test.ts`
  - 预期失败：文本答案对象被发送为 `selected_option_index`。
- RED: `cd frontend && npm test -- --run src/lib/quiz-state.test.ts`
  - 预期失败：混合分数为 `0.333...`，简答未满分未进入反馈列表。
- GREEN: `cd frontend && npm test -- --run src/lib/api.test.ts`
  - 结果：1 file passed, 15 tests passed。
- GREEN: `cd frontend && npm test -- --run src/lib/quiz-state.test.ts`
  - 结果：1 file passed, 16 tests passed。
- `cd frontend && npm test -- --run`
  - 结果：2 files passed, 31 tests passed。
- `cd frontend && npm run typecheck`
  - 结果：通过，`next typegen && tsc --noEmit`。
- `uv run pytest backend/tests/test_answer_api.py`
  - 结果：21 passed, 7 warnings。
- `cd frontend && npm run build`
  - 结果：Next.js production build 通过。

## 剩余/Blocker

- #18 本地行为完成。
- 未做真实浏览器人工点击验证；本轮以 frontend build/typecheck + public fetch boundary/state tests + backend answer route tests 作为可重复验证。
