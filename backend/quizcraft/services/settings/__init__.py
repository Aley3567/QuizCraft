"""settings 服务：LLM 配置的加密存储、读取与连通测试。"""
from quizcraft.services.settings.connection import (
    ConnectionResult,
    check_llm_connection,
)
from quizcraft.services.settings.crypto import (
    decrypt,
    decrypt_or_none,
    derive_fernet_key,
    encrypt,
    encrypt_or_none,
)
from quizcraft.services.settings.store import (
    LLMConfig,
    LLMConfigView,
    ReviewSettings,
    load_llm_config,
    load_llm_config_view,
    load_review_settings,
    save_llm_config,
    save_review_settings,
)

__all__ = [
    "ConnectionResult",
    "LLMConfig",
    "LLMConfigView",
    "ReviewSettings",
    "check_llm_connection",
    "decrypt",
    "decrypt_or_none",
    "derive_fernet_key",
    "encrypt",
    "encrypt_or_none",
    "load_llm_config",
    "load_llm_config_view",
    "load_review_settings",
    "save_llm_config",
    "save_review_settings",
]
