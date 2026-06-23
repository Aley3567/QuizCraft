"""应用配置。

LLM 默认 provider=mock，保证测试和无 key 环境下不依赖外部 API。
真实使用时通过环境变量配置 OpenAI 兼容端点：
    QUIZCRAFT_LLM_PROVIDER=openai
    QUIZCRAFT_LLM_API_KEY=...
    QUIZCRAFT_LLM_MODEL=gpt-4o
    QUIZCRAFT_LLM_BASE_URL=...   # 可选，指向 Claude/Ollama 等兼容端点
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="QUIZCRAFT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 数据库（async SQLite）
    db_url: str = "sqlite+aiosqlite:///./data/quizcraft.db"

    # 数据目录（上传文件、SQLite 等）
    data_dir: str = "./data"

    # LLM 抽象层
    # provider: mock（默认，测试用）| openai（OpenAI 兼容，覆盖 Claude/GPT via base_url）
    llm_provider: str = "mock"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o"
    llm_base_url: str | None = None


def get_settings() -> Settings:
    """读取当前环境配置（每次调用读最新环境变量）。"""
    return Settings()
