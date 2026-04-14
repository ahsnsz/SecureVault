import os
import secrets
import string
from app.dal.crypto_manager import CryptoManager

# Business Logic Layer (BLL)
# Responsible for coordinating between the GUI and DAL layers
# Handles file I/O and password generation
class VaultService:
    def __init__(self):
        # Instantiate the Data Access Layer (DAL) (i.e., crypto_manager)
        # and save it as a property in the BLL
        # This allows BLL to call the underlying encryption and decryption functions at any time
        self.crypto_manager = CryptoManager()

    # Generate random password
    def generate_random_password(self, length=16, use_upper=True, use_digits=True, use_symbols=True) -> str:

        # Password character set: uppercase and lowercase letters, numbers, and special characters
        chars = string.ascii_lowercase  # Default includes lowercase letters (a-z)
        if use_upper:
            chars += string.ascii_uppercase  # Add uppercase letters (A-Z)
        if use_digits:
            chars += string.digits  # Add numbers (0-9)
        if use_symbols:
            chars += "!@#$%^&*"  # Add special characters

        # Use the secrets module to generate a cryptographically secure random password
        # secrets.choice(chars) randomly selects a character from chars, repeats length times to generate a password of specified length
        # We don't use the random module because it generates pseudo-random numbers, while the secrets module uses system-level RNG, suitable for generating passwords and keys
        return ''.join(secrets.choice(chars) for _ in range(length))

    def evaluate_password_strength(self, password: str) -> tuple[str, str, float]:
        """
        Evaluate password strength
        Returns a tuple: (strength text, color hex, progress bar value 0.0~1.0)
        """
        if not password:
            return "", "transparent", 0.0

        score = 0
        # 1. Length bonus
        if len(password) >= 8: score += 1
        if len(password) >= 12: score += 1

        # 2. Complexity bonus
        if any(c.isupper() for c in password): score += 1
        if any(c.islower() for c in password): score += 1
        if any(c.isdigit() for c in password): score += 1
        if any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password): score += 1

        # 3. Rating and progress allocation
        if score < 3:
            return "Weak", "#d9534f", 0.33  # Red, 33% progress
        elif score < 5:
            return "Medium", "#f0ad4e", 0.66  # Orange, 66% progress
        else:
            return "Strong", "#5cb85c", 1.0  # Green, 100% progress

    # Implement password vault save functionality
    def save_vault(self, filepath: str, master_password: str, data: list):
        # Encrypts the user's plaintext password list and writes it to a local file.
        # 1. Call DAL: pass the plaintext data (data) and master password (master_password) to the encryption core
        # The returned encrypted_data is meaningless binary gibberish (bytes)
        encrypted_data = self.crypto_manager.encrypt_data(data, master_password)

        # 2. Write to local file
        # 'wb' means write binary.
        # Since the data after AES encryption is no longer plain text, it must be saved in binary mode.
        with open(filepath, 'wb') as f:
            f.write(encrypted_data)

    # Implement password vault load functionality
    def load_vault(self, filepath: str, master_password: str) -> list:
        """
        Read encrypted files from local storage and decrypt back to plaintext list.
        """
        # 1. Check if the file exists
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Cannot find vault file: {filepath}")

        # 2. Read binary file
        # 'rb' means Read Binary
        with open(filepath, 'rb') as f:
            encrypted_data = f.read()

        # 3. Call DAL: pass the read gibberish and user-entered master password to decrypt
        # If the password is wrong or the file has been tampered with, it will automatically report an error (ValueError written in DAL)
        decrypted_data = self.crypto_manager.decrypt_data(encrypted_data, master_password)

        # 4. Return plaintext data to GUI for display
        return decrypted_data

    # Implement the creation of a new empty password vault file
    def create_new_vault(self, filepath: str, master_password: str) -> list:
        """Create a new empty vault file"""
        empty_data = []  # Initially empty list
        self.save_vault(filepath, master_password, empty_data)
        return empty_data
        self.save_vault(filepath, master_password, empty_data)
        return empty_data