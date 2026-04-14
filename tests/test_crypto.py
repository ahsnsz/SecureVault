import pytest
import os
import json
from app.dal.crypto_manager import CryptoManager

# 测试夹具：每次测试前自动运行
@pytest.fixture
def crypto_manager():
    return CryptoManager()

def test_encrypt_decrypt_success(crypto_manager):
    """测试正常的加密和解密流程"""
    password = "StrongMasterPassword123!"
    secret_data = {
        "gmail": {"username": "user", "password": "abc"},
        "bank": {"username": "admin", "password": "123"}
    }

    # 1. 加密
    encrypted_blob = crypto_manager.encrypt_data(secret_data, password)

    # 验证生成了 bytes 数据，且长度肯定比原文长（因为加了 salt 和 nonce）
    assert isinstance(encrypted_blob, bytes)
    assert len(encrypted_blob) > len(json.dumps(secret_data))

    # 2. 解密
    decrypted_data = crypto_manager.decrypt_data(encrypted_blob, password)

    # 验证解密后的数据与原始内容一致
    assert decrypted_data == secret_data

def test_wrong_password(crypto_manager):
    """测试使用错误密码解密 (应失败)"""
    password = "RightPassword"
    wrong_password = "WrongPassword"
    data = {"secret": "value"}

    encrypted_blob = crypto_manager.encrypt_data(data, password)

    # 预期会抛出 ValueError (我们在代码里捕获了 InvalidTag 并转抛为 ValueError)
    with pytest.raises(ValueError, match="Invalid Password"):
        crypto_manager.decrypt_data(encrypted_blob, wrong_password)

def test_tampered_data(crypto_manager):
    """测试数据被篡改 (AES-GCM 完整性校验应失败)"""
    password = "password"
    data = {"secret": "value"}

    encrypted_blob = crypto_manager.encrypt_data(data, password)

    # 模拟黑客修改了文件的一个字节 (将最后一个字节改掉)
    tampered_blob = bytearray(encrypted_blob)
    tampered_blob[-1] = (tampered_blob[-1] + 1) % 256

    # 解密篡改后的数据应报错
    with pytest.raises(ValueError, match="Invalid Password or Corrupted Data"):
        crypto_manager.decrypt_data(bytes(tampered_blob), password)