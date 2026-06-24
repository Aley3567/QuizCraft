"""API key 对称加密服务。

切片 1.2 的 LLM 配置需把用户 API key 存入 SQLite settings 表；API key 是敏感凭证，
不能明文落库。用 Fernet（AES128-CBC + HMAC）对称加密，密钥从 QUIZCRAFT_SECRET_KEY
派生（SHA-256 → urlsafe base64），单机自部署足够。

Phase 4 的 JWT_SECRET 是另一回事（认证签发用）；Phase 1 尚无认证，本切片用通用 secret。
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def derive_fernet_key(secret: str) -> bytes:
    """从 secret 派生 Fernet key（32 字节 SHA-256 → urlsafe base64 编码）。

    空 secret 拒绝派生——不 fallback 弱密钥，避免静默用可预测值加密敏感数据。
    """
    if not secret:
        raise ValueError("secret 不能为空：配置 QUIZCRAFT_SECRET_KEY 后才能加密 API key")
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt(plaintext: str, secret: str) -> str:
    """加密明文，返回 Fernet token 字符串（可安全存入 DB 文本列）。"""
    fernet = Fernet(derive_fernet_key(secret))
    return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str, secret: str) -> str:
    """解密 Fernet token。

    secret 不匹配或密文损坏抛 ValueError——不静默返回脏数据，调用方需显式处理。
    """
    fernet = Fernet(derive_fernet_key(secret))
    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("解密失败：secret 不匹配或密文损坏") from exc


def encrypt_or_none(plaintext: str | None, secret: str) -> str | None:
    """None / 空串透传 None（API key 等可选字段不强制加密）。"""
    if not plaintext:
        return None
    return encrypt(plaintext, secret)


def decrypt_or_none(token: str | None, secret: str) -> str | None:
    """None 透传 None；否则解密。"""
    if token is None:
        return None
    return decrypt(token, secret)
