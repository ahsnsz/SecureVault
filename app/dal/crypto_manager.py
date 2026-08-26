import base64
import json
import os
from typing import Any, Dict, Tuple

from argon2.low_level import ARGON2_VERSION, Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoManager:
    """
    Data Access Layer security core.

    New vaults use the versioned v2 container. Existing pre-v2 vaults remain
    readable and will be upgraded automatically the next time they are saved.
    """

    # =====================================================================
    # PRIORITY-1 CHANGE 1: Versioned, self-describing vault file format.
    #
    # v2 binary layout:
    #   [MAGIC:4][VERSION:1][HEADER_LENGTH:4][HEADER:JSON][NONCE][CIPHERTEXT]
    #
    # The complete prefix through HEADER is authenticated as AES-GCM AAD.
    # Consequently, changing the version, KDF parameters, or salt causes
    # authentication to fail instead of silently changing decryption behavior.
    # =====================================================================
    MAGIC = b"SVDB"
    FORMAT_VERSION = 2
    HEADER_LENGTH_BYTES = 4
    MAX_HEADER_LENGTH = 16 * 1024
    GCM_NONCE_LENGTH = 12
    GCM_TAG_LENGTH = 16

    def __init__(self):
        # These values are written into each v2 file. They are data rather than
        # hidden application constants, so a future release can migrate KDF
        # settings while retaining the ability to read older files.
        self.kdf_params = {
            "name": "argon2id",
            "version": ARGON2_VERSION,
            "length": 32,
            "salt_len": 16,
            "time_cost": 2,
            "memory_cost": 64 * 1024,
            "parallelism": 4,
        }

    # =====================================================================
    # PRIORITY-1 CHANGE 2: Use argon2-cffi instead of the OpenSSL-dependent
    # cryptography Argon2id wrapper.
    #
    # Some valid Python/OpenSSL installations do not expose Argon2id through
    # cryptography. argon2-cffi provides the same standard Argon2id output and
    # can therefore decrypt both existing vaults and the new v2 format.
    # =====================================================================
    def _derive_key(
        self,
        password: str,
        salt: bytes,
        params: Dict[str, int] | None = None,
    ) -> bytes:
        selected = params or self.kdf_params
        return hash_secret_raw(
            secret=password.encode("utf-8"),
            salt=salt,
            time_cost=selected["time_cost"],
            memory_cost=selected["memory_cost"],
            parallelism=selected["parallelism"],
            hash_len=selected["length"],
            type=Type.ID,
            version=selected.get("version", ARGON2_VERSION),
        )

    def _build_header(self, salt: bytes) -> bytes:
        header = {
            "format": "SecureVault",
            "version": self.FORMAT_VERSION,
            "kdf": {
                "name": self.kdf_params["name"],
                "version": self.kdf_params["version"],
                "length": self.kdf_params["length"],
                "time_cost": self.kdf_params["time_cost"],
                "memory_cost": self.kdf_params["memory_cost"],
                "parallelism": self.kdf_params["parallelism"],
            },
            "cipher": {
                "name": "aes-256-gcm",
                "nonce_length": self.GCM_NONCE_LENGTH,
            },
            "salt": base64.b64encode(salt).decode("ascii"),
        }
        # Stable serialization makes the authenticated prefix deterministic
        # for a given header and avoids parser-dependent whitespace.
        return json.dumps(
            header,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def encrypt_data(self, data: Any, password: str) -> bytes:
        """Encrypt data into a versioned SecureVault v2 container."""
        salt = os.urandom(self.kdf_params["salt_len"])
        nonce = os.urandom(self.GCM_NONCE_LENGTH)
        key = self._derive_key(password, salt)

        header_bytes = self._build_header(salt)
        prefix = (
            self.MAGIC
            + bytes([self.FORMAT_VERSION])
            + len(header_bytes).to_bytes(self.HEADER_LENGTH_BYTES, "big")
            + header_bytes
        )

        plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, prefix)
        return prefix + nonce + ciphertext

    def decrypt_data(self, encrypted_data: bytes, password: str) -> Any:
        """
        Decrypt either a versioned v2 vault or a legacy salt/nonce/ciphertext
        vault. A successful save upgrades legacy data to v2 automatically.
        """
        try:
            if encrypted_data.startswith(self.MAGIC):
                return self._decrypt_v2(encrypted_data, password)
            return self._decrypt_legacy(encrypted_data, password)
        except InvalidTag as exc:
            # Wrong passwords and authenticated-data tampering intentionally
            # share one message so the file does not disclose which occurred.
            raise ValueError("Invalid Password or Corrupted Data") from exc
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Decryption failed: {exc}") from exc

    def _decrypt_v2(self, encrypted_data: bytes, password: str) -> Any:
        fixed_prefix_length = len(self.MAGIC) + 1 + self.HEADER_LENGTH_BYTES
        if len(encrypted_data) < fixed_prefix_length:
            raise ValueError("Data corrupted: incomplete vault header")

        version = encrypted_data[len(self.MAGIC)]
        if version != self.FORMAT_VERSION:
            raise ValueError(f"Unsupported vault format version: {version}")

        length_start = len(self.MAGIC) + 1
        length_end = length_start + self.HEADER_LENGTH_BYTES
        header_length = int.from_bytes(
            encrypted_data[length_start:length_end],
            "big",
        )
        if not 0 < header_length <= self.MAX_HEADER_LENGTH:
            raise ValueError("Data corrupted: invalid vault header length")

        header_end = fixed_prefix_length + header_length
        minimum_length = (
            header_end + self.GCM_NONCE_LENGTH + self.GCM_TAG_LENGTH
        )
        if len(encrypted_data) < minimum_length:
            raise ValueError("Data corrupted: truncated encrypted payload")

        header_bytes = encrypted_data[fixed_prefix_length:header_end]
        try:
            header = json.loads(header_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Data corrupted: invalid vault header") from exc

        salt, params, nonce_length = self._validate_header(header)
        nonce_end = header_end + nonce_length
        nonce = encrypted_data[header_end:nonce_end]
        ciphertext = encrypted_data[nonce_end:]
        authenticated_prefix = encrypted_data[:header_end]

        key = self._derive_key(password, salt, params)
        plaintext = AESGCM(key).decrypt(
            nonce,
            ciphertext,
            authenticated_prefix,
        )
        return json.loads(plaintext.decode("utf-8"))

    def _validate_header(
        self,
        header: Dict[str, Any],
    ) -> Tuple[bytes, Dict[str, int], int]:
        """
        Validate unauthenticated resource-cost fields before using them.

        Bounds prevent a malicious file from requesting extreme Argon2 memory,
        CPU, or thread counts before AES-GCM can authenticate the header.
        """
        if not isinstance(header, dict):
            raise ValueError("Data corrupted: vault header is not an object")
        if (
            header.get("format") != "SecureVault"
            or header.get("version") != self.FORMAT_VERSION
        ):
            raise ValueError("Data corrupted: invalid vault identity")

        kdf = header.get("kdf")
        cipher = header.get("cipher")
        if not isinstance(kdf, dict) or not isinstance(cipher, dict):
            raise ValueError("Data corrupted: missing crypto parameters")
        if kdf.get("name") != "argon2id":
            raise ValueError("Unsupported KDF")
        if cipher.get("name") != "aes-256-gcm":
            raise ValueError("Unsupported cipher")

        fields = (
            "version",
            "length",
            "time_cost",
            "memory_cost",
            "parallelism",
        )
        if any(
            not isinstance(kdf.get(field), int)
            or isinstance(kdf.get(field), bool)
            for field in fields
        ):
            raise ValueError("Data corrupted: invalid KDF parameters")

        params = {field: kdf[field] for field in fields}
        if params["version"] != ARGON2_VERSION:
            raise ValueError("Unsupported Argon2 version")
        if params["length"] != 32:
            raise ValueError("Unsupported derived-key length")
        if not 1 <= params["time_cost"] <= 10:
            raise ValueError("Unsafe Argon2 time cost")
        if not 8 * 1024 <= params["memory_cost"] <= 256 * 1024:
            raise ValueError("Unsafe Argon2 memory cost")
        if not 1 <= params["parallelism"] <= 16:
            raise ValueError("Unsafe Argon2 parallelism")

        nonce_length = cipher.get("nonce_length")
        if nonce_length != self.GCM_NONCE_LENGTH:
            raise ValueError("Unsupported AES-GCM nonce length")

        try:
            salt = base64.b64decode(header["salt"], validate=True)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Data corrupted: invalid salt") from exc
        if not 16 <= len(salt) <= 64:
            raise ValueError("Data corrupted: invalid salt length")

        return salt, params, nonce_length

    # =====================================================================
    # PRIORITY-1 CHANGE 3: Backward-compatibility reader.
    #
    # Legacy layout:
    #   [SALT:16][NONCE:12][CIPHERTEXT]
    #
    # Keeping this reader is essential: existing users can unlock old files,
    # and the next normal save writes the data in the safer v2 format.
    # =====================================================================
    def _decrypt_legacy(
        self,
        encrypted_data: bytes,
        password: str,
    ) -> Any:
        minimum_length = (
            self.kdf_params["salt_len"]
            + self.GCM_NONCE_LENGTH
            + self.GCM_TAG_LENGTH
        )
        if len(encrypted_data) < minimum_length:
            raise ValueError("Data corrupted: truncated legacy vault")

        salt_end = self.kdf_params["salt_len"]
        nonce_end = salt_end + self.GCM_NONCE_LENGTH
        salt = encrypted_data[:salt_end]
        nonce = encrypted_data[salt_end:nonce_end]
        ciphertext = encrypted_data[nonce_end:]

        key = self._derive_key(password, salt)
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode("utf-8"))
