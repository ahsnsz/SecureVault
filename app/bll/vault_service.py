import os
import secrets
import string
import tempfile
from pathlib import Path
from typing import Any, List

from app.dal.crypto_manager import CryptoManager


class VaultService:
    """
    Business Logic Layer coordinator.

    It owns password generation and durable vault-file persistence while the
    CryptoManager owns encryption and file-format parsing.
    """

    BACKUP_SUFFIX = ".bak"
    PRIVATE_FILE_MODE = 0o600

    def __init__(self):
        self.crypto_manager = CryptoManager()

    def generate_random_password(
        self,
        length=16,
        use_upper=True,
        use_digits=True,
        use_symbols=True,
    ) -> str:
        """Generate a password using the operating system CSPRNG."""
        chars = string.ascii_lowercase
        if use_upper:
            chars += string.ascii_uppercase
        if use_digits:
            chars += string.digits
        if use_symbols:
            chars += "!@#$%^&*"
        return "".join(secrets.choice(chars) for _ in range(length))

    def evaluate_password_strength(
        self,
        password: str,
    ) -> tuple[str, str, float]:
        """Return display text, color, and progress for the current password."""
        if not password:
            return "", "transparent", 0.0

        score = 0
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if any(c.isupper() for c in password):
            score += 1
        if any(c.islower() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password):
            score += 1

        if score < 3:
            return "Weak", "#d9534f", 0.33
        if score < 5:
            return "Medium", "#f0ad4e", 0.66
        return "Strong", "#5cb85c", 1.0

    # =====================================================================
    # PRIORITY-1 CHANGE 4: Crash-safe, atomic persistence.
    #
    # The old implementation opened the real vault with "wb", which truncated
    # it before the new ciphertext was safely stored. A crash, full disk, or
    # interrupted write could therefore destroy the only copy.
    #
    # The new sequence is:
    #   1. write a temporary file in the SAME directory;
    #   2. flush Python buffers and fsync the file;
    #   3. atomically replace the destination;
    #   4. fsync the containing directory where the OS supports it.
    #
    # Same-directory temporary files are important because os.replace is only
    # reliably atomic when source and destination are on the same filesystem.
    # =====================================================================
    def _atomic_write(self, target: Path, payload: bytes) -> None:
        target = Path(target)
        parent = target.parent
        if not parent.exists():
            raise FileNotFoundError(
                f"Destination directory does not exist: {parent}"
            )

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=str(parent),
        )
        descriptor_is_open = True
        temporary_path = Path(temporary_name)

        try:
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, self.PRIVATE_FILE_MODE)

            with os.fdopen(descriptor, "wb") as file:
                descriptor_is_open = False
                file.write(payload)
                file.flush()
                os.fsync(file.fileno())

            os.replace(temporary_path, target)
            # Vaults and backups should be readable only by the current user.
            # chmod is best-effort on Windows but effective on macOS/Linux.
            try:
                os.chmod(target, self.PRIVATE_FILE_MODE)
            except OSError:
                pass
            self._sync_directory(parent)
        finally:
            if descriptor_is_open:
                os.close(descriptor)
            # If any earlier operation failed, remove only our known temp file.
            # The original destination remains untouched.
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        """Durably record rename metadata where directory fsync is supported."""
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY

        try:
            directory_fd = os.open(str(directory), flags)
        except OSError:
            # Windows and some filesystems do not allow opening directories.
            return

        try:
            os.fsync(directory_fd)
        except OSError:
            pass
        finally:
            os.close(directory_fd)

    def save_vault(
        self,
        filepath: str,
        master_password: str,
        data: List[dict],
    ) -> None:
        """
        Encrypt and atomically save the complete vault.

        Before replacing an existing vault, preserve its previous encrypted
        generation as "<vault>.bak". The backup never contains plaintext.
        """
        encrypted_data = self.crypto_manager.encrypt_data(
            data,
            master_password,
        )
        target = Path(filepath).expanduser()

        # =================================================================
        # PRIORITY-1 CHANGE 5: Keep one recoverable encrypted generation.
        #
        # The backup is written atomically too. If writing the new main file
        # fails, the old main file is still present. If a later corruption is
        # discovered, the immediately previous encrypted version is available.
        # =================================================================
        if target.exists():
            with target.open("rb") as current_file:
                previous_encrypted_data = current_file.read()
            backup = Path(f"{target}{self.BACKUP_SUFFIX}")
            self._atomic_write(backup, previous_encrypted_data)

        self._atomic_write(target, encrypted_data)

    def load_vault(
        self,
        filepath: str,
        master_password: str,
    ) -> List[dict]:
        """Read and decrypt a vault file from local storage."""
        target = Path(filepath).expanduser()
        if not target.exists():
            raise FileNotFoundError(f"Cannot find vault file: {target}")

        with target.open("rb") as file:
            encrypted_data = file.read()

        decrypted_data = self.crypto_manager.decrypt_data(
            encrypted_data,
            master_password,
        )
        if not isinstance(decrypted_data, list) or any(
            not isinstance(item, dict) for item in decrypted_data
        ):
            raise ValueError("Invalid vault data structure")
        return decrypted_data

    def create_new_vault(
        self,
        filepath: str,
        master_password: str,
    ) -> List[dict]:
        """Create a new, empty v2 vault file."""
        empty_data: List[dict] = []
        self.save_vault(filepath, master_password, empty_data)
        return empty_data
