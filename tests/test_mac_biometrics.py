import pytest

from app.dal.mac_biometrics import (
    MacAuthManager,
    TouchIDAuthenticationError,
    TouchIDCredentialNotFoundError,
    TouchIDUnavailableError,
)


# ======================================================================
# PRIORITY-2 TOUCH ID TEST COVERAGE
#
# All macOS frameworks are injected as fakes. This keeps CI portable while
# proving vault isolation, authentication ordering, failure handling, timeout
# invalidation, Keychain deletion, and non-macOS lazy-loading behavior.
# ======================================================================
class FakeKeyring:
    def __init__(self):
        self.passwords = {}
        self.operations = []

    def set_password(self, service, account, password):
        self.operations.append(("set", service, account))
        self.passwords[(service, account)] = password

    def get_password(self, service, account):
        self.operations.append(("get", service, account))
        return self.passwords.get((service, account))

    def delete_password(self, service, account):
        self.operations.append(("delete", service, account))
        del self.passwords[(service, account)]


class FakeContext:
    def __init__(
        self,
        *,
        available=True,
        success=True,
        invoke_callback=True,
    ):
        self.available = available
        self.success = success
        self.invoke_callback = invoke_callback
        self.invalidated = False
        self.reuse_duration = None
        self.fallback_title = None
        self.reasons = []

    def init(self):
        return self

    def setTouchIDAuthenticationAllowableReuseDuration_(self, duration):
        self.reuse_duration = duration

    def setLocalizedFallbackTitle_(self, title):
        self.fallback_title = title

    def canEvaluatePolicy_error_(self, _policy, _error):
        return self.available, None

    def evaluatePolicy_localizedReason_reply_(
        self,
        _policy,
        reason,
        callback,
    ):
        self.reasons.append(reason)
        if self.invoke_callback:
            callback(self.success, None)

    def invalidate(self):
        self.invalidated = True


class FakeLocalAuthentication:
    LAPolicyDeviceOwnerAuthenticationWithBiometrics = 1

    def __init__(self, context):
        owner = self

        class LAContext:
            @classmethod
            def alloc(cls):
                return owner.context

        self.context = context
        self.LAContext = LAContext


def build_manager(context=None):
    fake_keyring = FakeKeyring()
    fake_context = context or FakeContext()
    fake_local_auth = FakeLocalAuthentication(fake_context)
    manager = MacAuthManager(
        platform_name="Darwin",
        keyring_backend=fake_keyring,
        local_auth_module=fake_local_auth,
    )
    return manager, fake_keyring, fake_context


def test_vault_account_name_is_stable_private_and_path_specific(tmp_path):
    first_path = tmp_path / "first.svdb"
    second_path = tmp_path / "second.svdb"

    first_id = MacAuthManager.account_name_for_vault(str(first_path))
    same_id = MacAuthManager.account_name_for_vault(
        str(tmp_path / "." / "first.svdb")
    )
    second_id = MacAuthManager.account_name_for_vault(str(second_path))

    assert first_id == same_id
    assert first_id != second_id
    assert first_id.startswith("vault:")
    assert str(first_path) not in first_id


def test_keychain_credentials_are_isolated_per_vault():
    manager, keyring_backend, _ = build_manager()

    manager.save_password_to_keychain("/vaults/one.svdb", "one-secret")
    manager.save_password_to_keychain("/vaults/two.svdb", "two-secret")

    assert (
        manager.get_password_from_keychain("/vaults/one.svdb")
        == "one-secret"
    )
    assert (
        manager.get_password_from_keychain("/vaults/two.svdb")
        == "two-secret"
    )
    assert len(keyring_backend.passwords) == 2


def test_authentication_completes_before_keychain_read():
    manager, keyring_backend, context = build_manager()
    vault_path = "/vaults/secure.svdb"
    manager.save_password_to_keychain(vault_path, "master-secret")
    keyring_backend.operations.clear()

    password = manager.authenticate_and_get_password(
        vault_path,
        reason="Test biometric unlock",
    )

    assert password == "master-secret"
    assert context.reasons == ["Test biometric unlock"]
    assert context.reuse_duration == 0.0
    assert context.fallback_title == ""
    assert keyring_backend.operations[0][0] == "get"


def test_missing_credential_is_reported_only_after_authentication():
    manager, _keyring_backend, context = build_manager()

    with pytest.raises(
        TouchIDCredentialNotFoundError,
        match="No Touch ID credential",
    ):
        manager.authenticate_and_get_password("/vaults/missing.svdb")

    assert context.reasons


def test_unavailable_or_failed_touch_id_has_safe_errors():
    unavailable_manager, _, _ = build_manager(
        FakeContext(available=False)
    )
    assert not unavailable_manager.is_available()
    with pytest.raises(TouchIDUnavailableError, match="unavailable"):
        unavailable_manager.authenticate()

    failed_manager, _, _ = build_manager(FakeContext(success=False))
    with pytest.raises(TouchIDAuthenticationError, match="not verified"):
        failed_manager.authenticate()
    assert not failed_manager.verify_touch_id()


def test_touch_id_timeout_invalidates_native_context():
    context = FakeContext(invoke_callback=False)
    manager, _, _ = build_manager(context)

    with pytest.raises(TouchIDAuthenticationError, match="timed out"):
        manager.authenticate(timeout_seconds=0.001)

    assert context.invalidated


def test_deleting_saved_credential_is_idempotent():
    manager, keyring_backend, _ = build_manager()
    vault_path = "/vaults/delete-me.svdb"
    manager.save_password_to_keychain(vault_path, "secret")
    keyring_backend.operations.clear()

    assert manager.delete_password_from_keychain(vault_path)
    assert not manager.delete_password_from_keychain(vault_path)
    assert not keyring_backend.passwords
    assert keyring_backend.operations[0][0] == "delete"
    assert all(
        operation[0] != "get"
        for operation in keyring_backend.operations
    )


def test_non_macos_path_does_not_import_optional_dependencies():
    manager = MacAuthManager(platform_name="Linux")

    assert not manager.is_available()
    with pytest.raises(TouchIDUnavailableError, match="only on macOS"):
        manager.save_password_to_keychain("/vault.svdb", "secret")
