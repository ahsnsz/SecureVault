import hashlib
import os
import platform
import threading
from typing import Any


class TouchIDError(RuntimeError):
    """Base exception for safe, user-displayable Touch ID failures."""


class TouchIDUnavailableError(TouchIDError):
    """Raised when macOS biometric or Keychain support is unavailable."""


class TouchIDAuthenticationError(TouchIDError):
    """Raised when biometric verification fails, is cancelled, or times out."""


class TouchIDCredentialNotFoundError(TouchIDError):
    """Raised when no Keychain credential exists for the selected vault."""


class TouchIDKeychainError(TouchIDError):
    """Raised when the macOS Keychain operation itself fails."""


class MacAuthManager:
    """
    Coordinate macOS Touch ID with a vault-specific Keychain credential.

    Optional macOS packages are imported lazily so the rest of SecureVault can
    still start and run on Windows/Linux, where requirements markers correctly
    skip those packages.
    """

    DEFAULT_REASON = "Unlock the selected SecureVault database"
    DEFAULT_TIMEOUT_SECONDS = 30.0
    BIOMETRICS_POLICY_FALLBACK = 1

    def __init__(
        self,
        service_name: str = "SecureVault",
        platform_name: str | None = None,
        keyring_backend: Any = None,
        local_auth_module: Any = None,
    ):
        self.service_name = service_name
        self._platform_name = platform_name or platform.system()
        self._keyring_backend = keyring_backend
        self._local_auth_module = local_auth_module

    # =====================================================================
    # PRIORITY-2 CHANGE 7A: Isolate credentials by canonical vault path.
    #
    # The old code stored every master password under one fixed "master_user"
    # account. Opening a second vault could overwrite the first credential or
    # return the wrong password. A one-way SHA-256 identifier gives each vault
    # its own stable Keychain account without exposing its path in Keychain.
    # =====================================================================
    @staticmethod
    def account_name_for_vault(vault_path: str) -> str:
        canonical_path = os.path.realpath(
            os.path.abspath(os.path.expanduser(vault_path))
        )
        path_digest = hashlib.sha256(
            canonical_path.encode("utf-8")
        ).hexdigest()
        return f"vault:{path_digest}"

    def is_mac(self) -> bool:
        return self._platform_name == "Darwin"

    def _get_keyring(self):
        if not self.is_mac():
            raise TouchIDUnavailableError(
                "Touch ID is available only on macOS."
            )

        if self._keyring_backend is not None:
            return self._keyring_backend

        try:
            import keyring
        except ImportError as error:
            raise TouchIDUnavailableError(
                "macOS Keychain support is not installed."
            ) from error

        self._keyring_backend = keyring
        return keyring

    def _get_local_authentication(self):
        if not self.is_mac():
            raise TouchIDUnavailableError(
                "Touch ID is available only on macOS."
            )

        if self._local_auth_module is not None:
            return self._local_auth_module

        try:
            import LocalAuthentication
        except ImportError as error:
            raise TouchIDUnavailableError(
                "macOS Touch ID support is not installed."
            ) from error

        self._local_auth_module = LocalAuthentication
        return LocalAuthentication

    def _new_context(self):
        local_auth = self._get_local_authentication()
        context = local_auth.LAContext.alloc().init()
        policy = getattr(
            local_auth,
            "LAPolicyDeviceOwnerAuthenticationWithBiometrics",
            self.BIOMETRICS_POLICY_FALLBACK,
        )

        # Require a fresh biometric check rather than reusing a recent result.
        if hasattr(
            context,
            "setTouchIDAuthenticationAllowableReuseDuration_",
        ):
            context.setTouchIDAuthenticationAllowableReuseDuration_(0.0)
        if hasattr(context, "setLocalizedFallbackTitle_"):
            context.setLocalizedFallbackTitle_("")

        return context, policy

    def is_available(self) -> bool:
        """Return whether this Mac can currently evaluate biometric policy."""
        try:
            context, policy = self._new_context()
            can_evaluate, _ = context.canEvaluatePolicy_error_(policy, None)
            return bool(can_evaluate)
        except Exception:
            return False

    # =====================================================================
    # PRIORITY-2 CHANGE 7B: Keychain access is explicit and vault-specific.
    #
    # No credential is written automatically. The GUI calls save only after
    # the user selects the opt-in checkbox and a password unlock succeeds.
    # Reads used for unlocking happen only after successful Touch ID.
    # =====================================================================
    def save_password_to_keychain(
        self,
        vault_path: str,
        password: str,
    ) -> None:
        if not password:
            raise ValueError("Cannot save an empty master password.")

        keyring_backend = self._get_keyring()
        account_name = self.account_name_for_vault(vault_path)
        try:
            keyring_backend.set_password(
                self.service_name,
                account_name,
                password,
            )
        except Exception as error:
            raise TouchIDKeychainError(
                "The master password could not be saved to Keychain."
            ) from error

    def get_password_from_keychain(
        self,
        vault_path: str,
    ) -> str | None:
        keyring_backend = self._get_keyring()
        account_name = self.account_name_for_vault(vault_path)
        try:
            return keyring_backend.get_password(
                self.service_name,
                account_name,
            )
        except Exception as error:
            raise TouchIDKeychainError(
                "The saved Keychain credential could not be read."
            ) from error

    def delete_password_from_keychain(self, vault_path: str) -> bool:
        """Delete the selected vault's credential; return False if absent."""
        keyring_backend = self._get_keyring()
        account_name = self.account_name_for_vault(vault_path)
        try:
            # Delete directly: checking existence with get_password would
            # materialize the master password in memory unnecessarily.
            keyring_backend.delete_password(
                self.service_name,
                account_name,
            )
            return True
        except Exception as error:
            if (
                isinstance(error, KeyError)
                or error.__class__.__name__ == "PasswordDeleteError"
            ):
                return False
            raise TouchIDKeychainError(
                "The saved Keychain credential could not be removed."
            ) from error

    # =====================================================================
    # PRIORITY-2 CHANGE 7C: Bounded, fresh biometric authentication.
    #
    # event.wait() previously had no timeout and could freeze the application
    # forever if the native callback never arrived. Every request now uses a
    # fresh LAContext, has a strict timeout, and invalidates timed-out context.
    # =====================================================================
    def authenticate(
        self,
        reason: str = DEFAULT_REASON,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Touch ID timeout must be positive.")

        context, policy = self._new_context()
        can_evaluate, _ = context.canEvaluatePolicy_error_(policy, None)
        if not can_evaluate:
            raise TouchIDUnavailableError(
                "Touch ID is unavailable or not enrolled on this Mac."
            )

        completion_event = threading.Event()
        authentication_result = {"success": False}

        def authentication_callback(success, _error):
            authentication_result["success"] = bool(success)
            completion_event.set()

        context.evaluatePolicy_localizedReason_reply_(
            policy,
            reason,
            authentication_callback,
        )

        if not completion_event.wait(timeout_seconds):
            if hasattr(context, "invalidate"):
                context.invalidate()
            raise TouchIDAuthenticationError(
                "Touch ID timed out. Please try again."
            )

        if not authentication_result["success"]:
            raise TouchIDAuthenticationError(
                "Touch ID was not verified."
            )

    def verify_touch_id(
        self,
        reason: str = DEFAULT_REASON,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> bool:
        """Compatibility helper returning False instead of raising."""
        try:
            self.authenticate(reason, timeout_seconds)
            return True
        except TouchIDError:
            return False

    def authenticate_and_get_password(
        self,
        vault_path: str,
        reason: str = DEFAULT_REASON,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> str:
        """
        Authenticate first, then fetch this vault's credential from Keychain.

        Keeping this order prevents the application from materializing the
        saved master password in process memory before biometric verification.
        """
        self.authenticate(reason, timeout_seconds)
        password = self.get_password_from_keychain(vault_path)
        if password is None:
            raise TouchIDCredentialNotFoundError(
                "No Touch ID credential is saved for this vault."
            )
        return password
