# QuizCraft

开源自部署的自适应学习引擎——从文档自动出题、智能教学、间隔复习、终端实操，四位一体。

核心差异化：做错题后，错题反馈引用**用户自己的文档原文**，而不是通用解析。

## 状态

Phase 1 · 切片 1.1「最小出题闭环」开发中。详见 `docs/plans/SLICE_PHASE_1.md`。

## 后端开发

```bash
# 安装依赖（含 dev 组）
uv sync

# 跑测试
uv run pytest

# 启动开发服务器
uv run uvicorn quizcraft.main:app --reload --port 8000
```

## 架构

详见 `docs/DESIGN_DECISIONS.md`。

- 后端：FastAPI + SQLAlchemy async + SQLite
- 前端：Next.js App Router（后续切片）
- LLM：可插拔抽象层，测试用 mock，不依赖真实 API key
