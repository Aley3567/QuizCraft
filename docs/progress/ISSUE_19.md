STATUS: COMPLETE

# ISSUE #19 - LLM settings UI and runtime smoke

## 本轮完成

- 领取最小编号 claimable issue：`gh#19 [TDD 1E] LLM settings UI and runtime smoke`。
- 读取本地 queue、TDD issue split、agent readiness、triage labels、issue tracker、issue body、PRD Phase 1、Slice Phase 1、相关源码/测试、近期 git log、Ralph review notes。
- TDD 红测：
  - 前端 `saveLlmSettings` / `getLlmSettings` public API 测试先失败于函数不存在。
  - 后端 `POST /api/settings/llm` 省略 `api_key` 的回归测试先失败于保存其他字段时清空已有 key。
- 最小绿码：
  - 前端新增 settings API 类型和 client：`GET /api/settings/llm` 只消费脱敏视图，`POST /api/settings/llm` 返回脱敏配置和 connection 结果。
  - 新增 `SettingsPanel`，在当前单页顶部提供 provider、model、API key、base URL 表单；保存后显示 key 是否已保存和连接检查结果。
  - 连接失败显示为黄色非致命反馈，不阻断页面继续上传和出题。
  - 后端 POST 语义修正：请求体未出现 `api_key` 时保留既有密钥；显式传 null/空值仍可清空，避免 Settings 页因 key 不回显而误删密钥。

## 验收项

- [x] Settings page saves provider, model, key, and base URL.
  - `SettingsPanel` 调用 `saveLlmSettings`，POST body 覆盖 provider/api_key/model/base_url。
- [x] GET settings shows masked key state only.
  - 前端类型和测试只消费 `has_api_key`；后端 settings API 测试继续断言响应不含明文 key。
- [x] Failed connection check returns a visible non-fatal result.
  - UI smoke 选择 `openai` 且不填 key，页面显示 `连接检查未通过：provider=openai 需要配置 api_key`，HTTP 仍为 200。
- [x] Saved DB config is used before environment fallback.
  - 既有 `backend/tests/test_llm_runtime_config.py` 路由集成测试覆盖 DB 配置优先于 env fallback，本轮复跑通过。
- [x] Tests do not require real LLM credentials.
  - 前端 fetch 测试用 mock Response；后端 settings/runtime 测试用 mock provider/monkeypatch，不发真实 LLM 请求。

## 验证

- RED: `cd frontend && npm test -- --run src/lib/api.test.ts`
  - 预期失败：`saveLlmSettings is not a function` / `getLlmSettings is not a function`。
- RED: `uv run pytest backend/tests/test_settings_api.py -q`
  - 预期失败：省略 `api_key` 后 `has_api_key` 从 true 变为 false。
- GREEN: `cd frontend && npm test -- --run src/lib/api.test.ts`
  - 结果：1 file passed, 17 tests passed。
- GREEN: `uv run pytest backend/tests/test_settings_api.py -q`
  - 结果：6 passed, 7 warnings。
- `cd frontend && npm test -- --run`
  - 结果：2 files passed, 33 tests passed。
- `cd frontend && npm run typecheck`
  - 结果：通过，`next typegen && tsc --noEmit`。
- `uv run pytest backend/tests/test_llm_runtime_config.py backend/tests/test_settings_api.py -q`
  - 结果：14 passed, 7 warnings。
- `cd frontend && npm run build`
  - 结果：Next.js production build 通过。
- `uv run pytest backend -q`
  - 结果：200 passed, 7 warnings。
- Render/UI smoke:
  - 启动 `uv run uvicorn quizcraft.main:app --app-dir backend --host 127.0.0.1 --port 8000` 和 `cd frontend && npm run dev`。
  - Chrome headless 打开 `http://localhost:3000`，桌面 1280x900 与移动 390x844 均无水平溢出。
  - UI 操作选择 `openai`、不填 key、点击保存，显示非致命黄色连接失败反馈。

## 剩余/Blocker

- #19 本地行为完成。
- 真实 provider credential validation 是 issue out of scope；真实 key、真实外网和本机 SOCKS/OpenAI 构造问题仍按全局 blocker 处理。
- 未修改 GitHub issue/label/PR，需下一轮 monitor 重新生成 `.codex-loop/queue.*` 后判断 #20 是否仍受远程 label/body 约束。
