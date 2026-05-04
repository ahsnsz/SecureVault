# Secure Vault - Password Manager
**University of Liverpool | COMP390 FYP 2025/26**
**Author:** Zhouyang Shen (201850515)

## Prerequisites
Ensure you have **Python 3.10 or higher** installed on your system.

## 😀 Installation & Setup

1. **Extract the ZIP file** and navigate to the project's root directory in your terminal/command prompt (the folder containing `main.py`).
   ```bash
   cd path/to/SecureVault
   ```

2. **Install the required dependencies** (CustomTkinter, Cryptography, Pytest).
   * **On macOS:**
     ```bash
     pip3 install -r requirements.txt
     ```
   * **On Windows:**
     ```bash
     pip install -r requirements.txt
     ```

## 😃 Running the Application

Once the dependencies are installed, you can launch the GUI application directly from the source code.

* **On macOS:**
  ```bash
  python3 main.py
  ```
* **On Windows:**
  ```bash
  python main.py
  


*(Note: The application dynamically resolves its local database path to the user's `Documents/SecureVault_Data` directory, ensuring persistent read/write capabilities across different operating systems.)*

## 😄 Running Automated Tests

automated testing for both the Data Access Layer (Cryptography) and the Business Logic Layer.

**1. Run Cryptographic Integrity Tests (pytest):**
To verify the AES-256-GCM encryption, Argon2id key derivation, and offline file tampering defenses:
```bash
pytest tests/
```

**2. Run Business Logic Tests (unittest):**
To verify the secure password generator and password strength evaluator boundaries:
```bash
python -m unittest discover tests
```

## 😁 Project Structure Highlights
* `app/`: Contains the core application logic (Presentation, Business Logic, and Data Access layers).
* `tests/`: Isolated directory containing all `pytest` and `unittest` scripts.
* `prototypes/`: Early iteration scripts for UI and Cryptography testing.
* `SecureVault.spec`: Configuration file demonstrating the `PyInstaller` build process for cross-platform packaging.