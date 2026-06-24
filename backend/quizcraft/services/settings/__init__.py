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
    load_llm_config,
    load_llm_config_view,
    save_llm_config,
)

__all__ = [
    "ConnectionResult",
    "LLMConfig",
    "LLMConfigView",
    "check_llm_connection",
    "decrypt",
    "decrypt_or_none",
    "derive_fernet_key",
    "encrypt",
    "encrypt_or_none",
    "load_llm_config",
    "load_llm_config_view",
    "save_llm_config",
]
