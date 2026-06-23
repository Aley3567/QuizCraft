"""API 路由汇总。"""
from quizcraft.routers.documents import router as documents_router
from quizcraft.routers.quiz import router as quiz_router

__all__ = ["documents_router", "quiz_router"]
