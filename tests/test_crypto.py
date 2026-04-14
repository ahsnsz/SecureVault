import pytest
import os
import json
from app.dal.crypto_manager import CryptoManager

# Test fixture: automatically run before each test
@pytest.fixture
def crypto_manager():
    return CryptoManager()

def test_encrypt_decrypt_success(crypto_manager):
    """Test normal encryption and decryption process"""
    password = "StrongMasterPassword123!"
    secret_data = {
        "gmail": {"username": "user", "password": "abc"},
        "bank": {"username": "admin", "password": "123"}
    }

    # 1. Encrypt
    encrypted_blob = crypto_manager.encrypt_data(secret_data, password)

    # Verify that bytes data is generated and length is definitely longer than original (because salt and nonce are added)
    assert isinstance(encrypted_blob, bytes)
    assert len(encrypted_blob) > len(json.dumps(secret_data))

    # 2. Decrypt
    decrypted_data = crypto_manager.decrypt_data(encrypted_blob, password)

    # Verify that the decrypted data is consistent with the original content
    assert decrypted_data == secret_data

def test_wrong_password(crypto_manager):
    """Test decryption with wrong password (should fail)"""
    password = "RightPassword"
    wrong_password = "WrongPassword"
    data = {"secret": "value"}

    encrypted_blob = crypto_manager.encrypt_data(data, password)

    # Expected to throw ValueError (we catch InvalidTag in the code and rethrow as ValueError)
    with pytest.raises(ValueError, match="Invalid Password"):
        crypto_manager.decrypt_data(encrypted_blob, wrong_password)

def test_tampered_data(crypto_manager):
    """Test data tampering (AES-GCM integrity check should fail)"""
    password = "password"
    data = {"secret": "value"}

    encrypted_blob = crypto_manager.encrypt_data(data, password)

    # Simulate hacker modifying one byte of the file (changing the last byte)
    tampered_blob = bytearray(encrypted_blob)
    tampered_blob[-1] = (tampered_blob[-1] + 1) % 256

    # Decryption of tampered data should raise an error
    with pytest.raises(ValueError, match="Invalid Password or Corrupted Data"):
        crypto_manager.decrypt_data(bytes(tampered_blob), password)