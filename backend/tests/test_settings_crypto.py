"""settings 加密服务测试：Fernet 对称加密 API key，secret 派生自 QUIZCRAFT_SECRET_KEY。

纯逻辑，不碰 DB。覆盖：派生确定性、加解密 round-trip、secret 不匹配失败、
空 secret 拒绝、None 透传（API key 可选字段不强制加密）。
"""
import pytest

from quizcraft.services.settings.crypto import (
    decrypt,
    decrypt_or_none,
    derive_fernet_key,
    encrypt,
    encrypt_or_none,
)

SECRET = "test-quizcraft-secret-please-rotate"


def test_derive_key_is_deterministic():
    """同一 secret 派生同一 Fernet key（重启/重启后能解密历史数据）。"""
    assert derive_fernet_key(SECRET) == derive_fernet_key(SECRET)


def test_derive_key_differs_across_secrets():
    """不同 secret 派生不同 key（隔离不同部署的密文）。"""
    assert derive_fernet_key(SECRET) != derive_fernet_key("another-secret")


def test_encrypt_decrypt_roundtrip():
    """加密后用同一 secret 解密还原明文（含 CJK，覆盖 API key 与中文 model 名）。"""
    plaintext = "sk-proj-abc中文key-123"
    token = encrypt(plaintext, SECRET)
    assert token != plaintext  # 密文确实变了
    assert decrypt(token, SECRET) == plaintext


def test_decrypt_wrong_secret_raises():
    """用错误 secret 解密抛 ValueError（不静默返回脏数据）。"""
    token = encrypt("sk-real-key", SECRET)
    with pytest.raises(ValueError, match="secret"):
        decrypt(token, "wrong-secret")


def test_encrypt_empty_secret_raises():
    """空 secret 拒绝加密（不 fallback 弱密钥，对齐安全取向）。"""
    with pytest.raises(ValueError, match="secret"):
        encrypt("sk-x", "")


def test_encrypt_or_none_passthrough_none():
    """API key 可选字段为 None 时透传 None（不强制加密缺失字段）。"""
    assert encrypt_or_none(None, SECRET) is None
    assert encrypt_or_none("", SECRET) is None


def test_decrypt_or_none_passthrough_none():
    """密文为 None 时透传 None。"""
    assert decrypt_or_none(None, SECRET) is None


def test_roundtrip_via_or_none_helpers():
    """encrypt_or_none / decrypt_or_none round-trip。"""
    token = encrypt_or_none("sk-or-none-key", SECRET)
    assert decrypt_or_none(token, SECRET) == "sk-or-none-key"
