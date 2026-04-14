import os
import json
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag

class CryptoManager:
    """
    Data Access Layer (DAL) Security Core.
    Responsible for handling all encryption (AES-GCM) and key derivation (Argon2id)
    """

    def __init__(self):
        # Configure Argon2id parameters
        # According to the detailed proposal, we need to resist GPU attacks, so we need high memory consumption.
        self.kdf_params = {
            "algorithm": hashes.SHA256(),
            "length": 32,  # Generate 32 bytes (256-bit) key corresponding to AES-256
            "salt_len": 16,  # 16 bytes random Salt
            "iterations": 2,  # Number of iterations (Time cost)
            "memory_cost": 64 * 1024,  # Memory consumption 64MB (Memory cost) to resist GPU attacks
            "parallelism": 4,  # Degree of parallelism
        }


    def _derive_key(self, password: str, salt: bytes) -> bytes:
        # Key derivation
        # The user's password length is variable and not random.
        # The AES encryption algorithm requires a fixed-length (32-byte) and seemingly random binary string as the Key.
        # KDF (Key Derivation Function) is responsible for converting a "weak password" into a "strong key".
        # Salt (salt) function: If no salt is added, two users with the same password "123456" would generate the same Key.
        # With random salt, even if passwords are the same, the generated Key is completely different, preventing "rainbow table" attacks.
        """
        Internal method: Use Argon2id to convert user master password to encryption key.
        """
        kdf = Argon2id(
            salt=salt,
            length=self.kdf_params["length"],
            iterations=self.kdf_params["iterations"],
            memory_cost=self.kdf_params["memory_cost"],
            lanes=self.kdf_params["parallelism"]
        )
        # Convert string password to bytes and derive
        # return kdf.derive(password.encode('utf-8'))
        # 1. Derive 32 bytes of binary Key
        key = kdf.derive(password.encode('utf-8'))

        # # ==========================================
        # # 🛠️ Temporary debug code: Watch the Key being created
        # # ==========================================
        # print("\n" + "=" * 40)
        # print("🔐 [Security Core Execution Log] Key derivation successful!")
        # print(f"👉 Plaintext password entered by user: {password}")
        # print(f"🧂 Randomly generated Salt (hexadecimal): {salt.hex()}")
        # print(f"🔑 Derived AES Key (hexadecimal): {key.hex()}")
        # print(f"📏 Exact length of Key: {len(key)} bytes (corresponding to AES-256)")
        # print("=" * 40 + "\n")
        # # ==========================================

        return key

    def encrypt_data(self, data: dict, password: str) -> bytes:
        """
        Encryption process:
        1. Generate random Salt
        2. Derive key (Key)
        3. Generate random Nonce
        4. AES-GCM encryption
        5. Package and return (Salt + Nonce + Ciphertext)
        """
        # 1. Generate unique random Salt
        salt = os.urandom(self.kdf_params["salt_len"])

        # 2. Derive key (AES-256 Key) [Create key: use salt + password -> calculate AES Key]
        key = self._derive_key(password, salt)

        # 3. Initialize AES-GCM and generate Nonce (IV) [AES-GCM needs a "one-time number" (Nonce), must never repeat]
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # GCM standard recommends 12-byte Nonce

        # Prepare data: convert dictionary to JSON string then to bytes
        json_data = json.dumps(data).encode('utf-8')

        # 4. Encrypt
        ciphertext = aesgcm.encrypt(nonce, json_data, None)

        # 5. Package: For convenient decryption, we need to store Salt and Nonce together with the ciphertext
        # Format: [Salt (16 bytes)] [Nonce (12 bytes)] [Ciphertext (remaining)]
        return salt + nonce + ciphertext


    def decrypt_data(self, encrypted_data: bytes, password: str) -> dict:
        """
        Decryption process:
        1. Extract Salt and Nonce
        2. Re-derive key
        3. AES-GCM decryption (automatically verify integrity)
        """
        try:
            # Check if data length is valid (must have at least Salt + Nonce)
            if len(encrypted_data) < 28:
                raise ValueError("Data corrupted")

            # 1. Extract header information [Unpack: slice in the order they were stored]
            salt = encrypted_data[:16] # First 16 bytes is salt
            nonce = encrypted_data[16:28] # Next 12 bytes is Nonce
            ciphertext = encrypted_data[28:] # The rest is ciphertext

            # 2. Use the same parameters and Salt to re-derive the key [Restore key: use read Salt + user-entered password -> calculate Key]
            key = self._derive_key(password, salt)

            # 3. Decrypt
            aesgcm = AESGCM(key)
            # decrypt method automatically verifies Tag, raises InvalidTag exception if not matched [This step is for identity verification]
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)

            # Convert back to dictionary
            return json.loads(plaintext_bytes.decode('utf-8'))

        except InvalidTag:
            # This is the characteristic of AES-GCM, if the password is wrong or the file has been tampered with, Tag verification will fail
            raise ValueError("Invalid Password or Corrupted Data")
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")