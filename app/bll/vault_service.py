import os
import secrets
import string
import tempfile
from pathlib import Path
from typing import List

from app.dal.crypto_manager import CryptoManager


class VaultService:
    """
    Business Logic Layer coordinator.

    It owns password generation and durable vault-file persistence while the
    CryptoManager owns encryption and file-format parsing.
    """

    BACKUP_SUFFIX = ".bak"
    PRIVATE_FILE_MODE = 0o600
    PASSWORD_SYMBOLS = "!@#$%^&*"
    MIN_MASTER_PASSWORD_LENGTH = 12
    COMMON_WEAK_PASSWORDS = frozenset(
        {
            "password",
            "password123",
            "123456789012",
            "qwertyuiop12",
            "letmein123456",
        }
    )

    def __init__(self):
        self.crypto_manager = CryptoManager()

    # =====================================================================
    # PRIORITY-2 CHANGE 1: Guarantee every requested character category.
    #
    # Choosing every position from one combined pool only made uppercase,
    # digits, and symbols probable. It did not guarantee them. We now select
    # one character from each enabled category, fill the remaining positions
    # with the OS-backed CSPRNG, and securely shuffle the final list.
    # =====================================================================
    def generate_random_password(
        self,
        length=16,
        use_upper=True,
        use_digits=True,
        use_symbols=True,
    ) -> str:
        """Generate a password that includes every enabled character class."""
        if not isinstance(length, int) or isinstance(length, bool):
            raise TypeError("Password length must be an integer")

        categories = [string.ascii_lowercase]
        if use_upper:
            categories.append(string.ascii_uppercase)
        if use_digits:
            categories.append(string.digits)
        if use_symbols:
            categories.append(self.PASSWORD_SYMBOLS)

        if length < len(categories):
            raise ValueError(
                "Password length is too short for the selected character classes"
            )

        password_chars = [secrets.choice(category) for category in categories]
        combined_pool = "".join(categories)
        password_chars.extend(
            secrets.choice(combined_pool)
            for _ in range(length - len(password_chars))
        )
        secrets.SystemRandom().shuffle(password_chars)
        return "".join(password_chars)

    # =====================================================================
    # PRIORITY-2 CHANGE 2: One master-password policy for create and change.
    #
    # Existing vaults remain unlockable with their original password. The
    # policy is applied only when a new credential is created, preventing new
    # weak credentials without locking users out of legacy vaults.
    # =====================================================================
    def validate_master_password(self, password: str) -> tuple[bool, str]:
        """Validate a newly created master password and return UI feedback."""
        if len(password) < self.MIN_MASTER_PASSWORD_LENGTH:
            return (
                False,
                f"Use at least {self.MIN_MASTER_PASSWORD_LENGTH} characters.",
            )

        if password.casefold() in self.COMMON_WEAK_PASSWORDS:
            return False, "This password is too common. Choose a unique phrase."

        if len(set(password)) == 1:
            return False, "Do not use the same character repeatedly."

        category_count = sum(
            (
                any(character.islower() for character in password),
                any(character.isupper() for character in password),
                any(character.isdigit() for character in password),
                any(not character.isalnum() for character in password),
            )
        )
        if category_count < 3:
            return (
                False,
                "Use at least three types: lowercase, uppercase, numbers, symbols.",
            )

        return True, ""

    # =====================================================================
    # PRIORITY-2 CHANGE 3: Stable, unique identifiers for password entries.
    #
    # Display fields are not identities: two records may legitimately contain
    # exactly the same site, username, and password. IDs let edit/delete target
    # one record unambiguously. Legacy entries receive IDs in a copied list so
    # a failed save never mutates the last committed in-memory state.
    # =====================================================================
    @staticmethod
    def create_entry_id() -> str:
        """Return a cryptographically random 128-bit entry identifier."""
        return secrets.token_hex(16)

    def ensure_entry_ids(self, data: List[dict]) -> List[dict]:
        """Return copied entries with non-empty, unique IDs."""
        prepared_entries = []
        seen_ids = set()

        for item in data:
            prepared_entry = dict(item)
            entry_id = prepared_entry.get("id")
            if (
                not isinstance(entry_id, str)
                or not entry_id
                or entry_id in seen_ids
            ):
                entry_id = self.create_entry_id()
                while entry_id in seen_ids:
                    entry_id = self.create_entry_id()

            prepared_entry["id"] = entry_id
            seen_ids.add(entry_id)
            prepared_entries.append(prepared_entry)

        return prepared_entries

    @staticmethod
    def find_entry_index(data: List[dict], entry_id: str) -> int:
        """Find an entry by stable ID instead of equality of display fields."""
        for index, item in enumerate(data):
            if item.get("id") == entry_id:
                return index
        raise ValueError("Password entry no longer exists")

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
