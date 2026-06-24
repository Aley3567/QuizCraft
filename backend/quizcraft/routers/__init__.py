"""API 路由汇总。"""
from quizcraft.routers.documents import router as documents_router
from quizcraft.routers.flashcards import router as flashcards_router
from quizcraft.routers.questions import router as questions_router
from quizcraft.routers.quiz import router as quiz_router
from quizcraft.routers.quiz_sessions import router as quiz_sessions_router
from quizcraft.routers.settings import router as settings_router

__all__ = [
    "documents_router",
    "flashcards_router",
    "questions_router",
    "quiz_router",
    "quiz_sessions_router",
    "settings_router",
]
