# SecureVault - Password Manager

[中文说明与完整打包指南](README_zh.md)

**University of Liverpool | COMP390 FYP 2025/26**

**Author:** Zhouyang Shen (201850515)

SecureVault is a local desktop password manager built with Python and
CustomTkinter. Vault data is encrypted on disk with AES-256-GCM, and the
encryption key is derived from the master password with Argon2id.

<!--
PRIORITY-2 DOCUMENTATION UPDATE:
This README now matches the current security model, Touch ID workflow,
dependency split, test suite, and PyInstaller specification.
-->

## Features

- Create, open, switch, lock, and delete encrypted `.svdb` vaults.
- Add, search, edit, copy, and delete password records.
- Generate cryptographically secure passwords with guaranteed selected
  character categories.
- Protect new master passwords with one consistent password policy.
- Auto-lock an open vault after 5 minutes of inactivity.
- Clear an application-owned copied password after 30 seconds without
  overwriting newer clipboard content copied by another application.
- Use optional, vault-specific Touch ID unlock on supported Macs.
- Save vault updates atomically and keep a `.bak` recovery copy.
- Continue opening vaults created with the earlier SecureVault file format.

## Requirements

- Anaconda or Miniconda for source development and packaging
- Python 3.10 in the Conda environment named `securevault`
- Windows or macOS for the desktop interface
- macOS with Touch ID enrolled to use biometric unlock

Runtime dependencies are pinned in `requirements.txt`. Test and packaging
tools are kept separately in `requirements-dev.txt`. The packaged application
contains its Python runtime, so end users do not need Anaconda or Python.

## Installation

### Install from source

1. Extract or clone the project and enter its root directory:

   ```bash
   cd path/to/SecureVault
   ```

2. Create the standard Conda environment if it does not already exist, then
   activate it:

   ```bash
   conda create --name securevault python=3.10 -y
   conda activate securevault
   ```

   On this development Mac, the existing environment's interpreter is:

   ```text
   /opt/anaconda3/envs/securevault/bin/python
   ```

   The absolute path is machine-specific. On every platform, activate by the
   environment name and verify the interpreter instead of hard-coding a path:

   ```bash
   python -c "import sys; print(sys.executable)"
   python --version
   ```

3. Install the runtime dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

   The Touch ID packages use a macOS environment marker, so pip skips them
   automatically on Windows and other operating systems.

### Install the packaged macOS application

If the Homebrew release is available:

```bash
brew tap ahsnsz/securevault
brew install --cask securevault
```

## Run the application

Activate the standard environment and run from the project root:

```bash
conda activate securevault
python main.py
```

The default vault and recent-vault list are stored in:

```text
~/Documents/SecureVault_Data/
```

You can select another `.svdb` path from the login screen.

## Create or unlock a vault

### Create a new vault

1. Select a new vault path or use the default path.
2. Enter the new master password twice.
3. Select **Enable Touch ID after successful password unlock** if you want to
   opt in on a supported Mac.
4. Select **Unlock / Create Vault**.

New master passwords must:

- contain at least 12 characters;
- use at least three of these categories: lowercase letters, uppercase
  letters, numbers, and symbols;
- not be a known common password; and
- not repeat the same character for the entire password.

The new policy applies when creating a vault or changing its master password.
Existing vaults can still be opened with their original master password.

### Unlock an existing vault with its password

1. Select the vault from **Recent Vaults** or choose its file.
2. Enter its master password.
3. Optionally select **Enable Touch ID after successful password unlock**.
4. Select **Unlock / Create Vault**.

SecureVault does not retain a failed master-password attempt as session state.

## Use Touch ID on macOS

Touch ID is optional and is enabled separately for each vault. The saved
credential is stored in the current macOS user's Keychain under an identifier
derived from the selected vault path.

To enable it:

1. Confirm that Touch ID is enrolled in macOS System Settings.
2. Open the vault once with its current master password.
3. Before unlocking, select **Enable Touch ID after successful password
   unlock**.
4. Complete the normal password unlock. SecureVault saves the credential only
   after the vault has been opened successfully.

On a later launch, select the same vault and choose **Unlock with Touch ID**.
SecureVault performs biometric authentication before reading the saved
credential. A request times out after 30 seconds, and password unlock always
remains available.

To remove the saved Touch ID credential, open the vault and go to:

```text
Settings > Touch ID > Forget Touch ID Credential
```

Deleting a vault through SecureVault also removes its saved Touch ID
credential. If the master password changes while Touch ID is enabled for the
current session, the Keychain credential is updated after the encrypted vault
has been replaced successfully.

## Install development tools and run tests

Install the runtime, test, and packaging dependencies together:

```bash
conda activate securevault
python -m pip install -r requirements-dev.txt
```

Run the complete automated test suite:

```bash
python -m pytest tests -v
```

The suite covers encryption and tamper detection, file-format compatibility,
atomic persistence and backup recovery, master-password validation, password
generation, stable record IDs, clipboard ownership, and portable Touch ID
behavior with mocked macOS services.

## Build a standalone application

Install the development dependencies, then build with the checked-in
PyInstaller specification:

```bash
conda activate securevault
python -m pip install -r requirements-dev.txt
python -m PyInstaller --clean --noconfirm SecureVault.spec
```

Build output is written to `dist/`. The specification declares the lazy
Touch ID and macOS Keychain imports required by the packaged macOS app.

## Project structure

```text
SecureVault/
├── app/
│   ├── bll/                 # Password policy and vault business logic
│   ├── dal/                 # Encryption, persistence, and Touch ID/Keychain
│   └── gui/                 # CustomTkinter interface
├── tests/                   # Automated tests
├── main.py                  # Application entry point
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # Test and packaging dependencies
└── SecureVault.spec         # PyInstaller build configuration
```

## Security notes

- Keep the master password safe. SecureVault has no password-recovery service.
- Do not share `.svdb` files together with their master password.
- Touch ID convenience does not replace encryption; the master password is
  still required to derive the vault's encryption key.
- Python cannot guarantee complete in-memory zeroization of immutable strings,
  but SecureVault removes sensitive session references and owned clipboard
  content when locking, logging out, or closing.
