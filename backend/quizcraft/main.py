"""FastAPI 应用入口。"""
from fastapi import FastAPI

from quizcraft import __version__
from quizcraft.routers import documents_router, quiz_router

app = FastAPI(title="QuizCraft API", version=__version__)

app.include_router(documents_router)
app.include_router(quiz_router)


@app.get("/health")
async def health() -> dict:
    """健康检查。"""
    return {"status": "ok"}
