"""FastAPI 应用入口。"""
from fastapi import FastAPI

from quizcraft import __version__

app = FastAPI(title="QuizCraft API", version=__version__)


@app.get("/health")
async def health() -> dict:
    """健康检查。"""
    return {"status": "ok"}
