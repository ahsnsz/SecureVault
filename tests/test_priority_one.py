import json
import os
import stat
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.bll.vault_service import VaultService
from app.dal.crypto_manager import CryptoManager


PASSWORD = "PriorityOne-Test-Master-Password!"


# ======================================================================
# PRIORITY-1 TEST COVERAGE
#
# These tests protect the new durable-storage contract:
# - new vaults carry a versioned and authenticated header;
# - legacy vaults remain readable and migrate on the next save;
# - interrupted writes preserve the previous vault;
# - one encrypted backup generation is retained;
# - vault and backup files use private permissions.
# ======================================================================
def _legacy_encrypt(manager, data, password):
    """Create the exact pre-v2 format for migration testing."""
    salt = os.urandom(manager.kdf_params["salt_len"])
    nonce = os.urandom(manager.GCM_NONCE_LENGTH)
    key = manager._derive_key(password, salt)
    plaintext = json.dumps(data).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    return salt + nonce + ciphertext


def test_new_vault_uses_versioned_authenticated_format():
    manager = CryptoManager()
    data = [{"site": "Example", "password": "secret"}]

    encrypted = manager.encrypt_data(data, PASSWORD)

    assert encrypted.startswith(manager.MAGIC)
    assert encrypted[len(manager.MAGIC)] == manager.FORMAT_VERSION
    assert manager.decrypt_data(encrypted, PASSWORD) == data


def test_authenticated_header_tampering_is_rejected():
    manager = CryptoManager()
    encrypted = bytearray(manager.encrypt_data([], PASSWORD))

    salt_marker = b'"salt":"'
    salt_start = bytes(encrypted).index(salt_marker) + len(salt_marker)
    encrypted[salt_start] = (
        ord("B") if encrypted[salt_start] == ord("A") else ord("A")
    )

    with pytest.raises(ValueError):
        manager.decrypt_data(bytes(encrypted), PASSWORD)


def test_unknown_future_format_version_is_rejected():
    manager = CryptoManager()
    encrypted = bytearray(manager.encrypt_data([], PASSWORD))
    encrypted[len(manager.MAGIC)] = manager.FORMAT_VERSION + 1

    with pytest.raises(ValueError, match="Unsupported vault format version"):
        manager.decrypt_data(bytes(encrypted), PASSWORD)


def test_legacy_vault_loads_and_migrates_on_next_save(tmp_path):
    service = VaultService()
    vault_path = tmp_path / "legacy.svdb"
    original_data = [{"site": "Legacy", "password": "old-secret"}]
    legacy_blob = _legacy_encrypt(
        service.crypto_manager,
        original_data,
        PASSWORD,
    )
    vault_path.write_bytes(legacy_blob)

    loaded = service.load_vault(str(vault_path), PASSWORD)
    assert loaded == original_data

    service.save_vault(str(vault_path), PASSWORD, loaded)

    assert vault_path.read_bytes().startswith(
        service.crypto_manager.MAGIC
    )
    backup_path = Path(f"{vault_path}{service.BACKUP_SUFFIX}")
    assert backup_path.read_bytes() == legacy_blob


def test_atomic_save_keeps_encrypted_backup_and_private_permissions(
    tmp_path,
):
    service = VaultService()
    vault_path = tmp_path / "vault.svdb"
    first_data = [{"site": "First", "password": "one"}]
    second_data = [{"site": "Second", "password": "two"}]

    service.save_vault(str(vault_path), PASSWORD, first_data)
    first_generation = vault_path.read_bytes()
    service.save_vault(str(vault_path), PASSWORD, second_data)

    backup_path = Path(f"{vault_path}{service.BACKUP_SUFFIX}")
    assert service.load_vault(str(vault_path), PASSWORD) == second_data
    assert backup_path.read_bytes() == first_generation
    assert service.crypto_manager.decrypt_data(
        backup_path.read_bytes(),
        PASSWORD,
    ) == first_data

    if os.name != "nt":
        assert stat.S_IMODE(vault_path.stat().st_mode) == 0o600
        assert stat.S_IMODE(backup_path.stat().st_mode) == 0o600


def test_interrupted_replace_preserves_previous_vault(
    tmp_path,
    monkeypatch,
):
    service = VaultService()
    vault_path = tmp_path / "vault.svdb"
    original_data = [{"site": "Stable", "password": "original"}]
    replacement_data = [{"site": "New", "password": "replacement"}]

    service.save_vault(str(vault_path), PASSWORD, original_data)
    original_blob = vault_path.read_bytes()
    real_replace = os.replace

    def fail_only_main_vault_replace(source, destination):
        if Path(destination) == vault_path:
            raise OSError("simulated interrupted replacement")
        return real_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_only_main_vault_replace)

    with pytest.raises(OSError, match="simulated interrupted"):
        service.save_vault(
            str(vault_path),
            PASSWORD,
            replacement_data,
        )

    assert vault_path.read_bytes() == original_blob
    assert service.load_vault(str(vault_path), PASSWORD) == original_data
    assert not list(tmp_path.glob(".*.tmp"))


def test_service_rejects_non_list_vault_payload(tmp_path):
    service = VaultService()
    vault_path = tmp_path / "invalid-structure.svdb"
    vault_path.write_bytes(
        service.crypto_manager.encrypt_data(
            {"unexpected": "object"},
            PASSWORD,
        )
    )

    with pytest.raises(ValueError, match="Invalid vault data structure"):
        service.load_vault(str(vault_path), PASSWORD)
