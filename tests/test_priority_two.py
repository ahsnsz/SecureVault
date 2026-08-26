import string

import pytest

from app.bll.vault_service import VaultService
from app.gui.app_ui import SecureVaultApp


# ======================================================================
# PRIORITY-2 TEST COVERAGE
#
# These tests protect the user-visible security improvements:
# - generated passwords always contain every requested character class;
# - new master passwords follow one explicit policy;
# - visually identical records retain separate stable identities;
# - clipboard cleanup never destroys content copied by another application.
# ======================================================================
class ClipboardStub:
    """Minimal non-GUI object for exercising clipboard ownership logic."""

    def __init__(self, copied_password, current_clipboard):
        self.clipboard_timer = "timer-id"
        self.copied_password_value = copied_password
        self.current_clipboard = current_clipboard
        self.cancelled_timers = []
        self.clear_count = 0
        self.toast_messages = []

    def after_cancel(self, timer_id):
        self.cancelled_timers.append(timer_id)

    def clipboard_get(self):
        return self.current_clipboard

    def clipboard_clear(self):
        self.clear_count += 1
        self.current_clipboard = ""

    def update(self):
        pass

    def show_toast(self, message, text_color="white"):
        self.toast_messages.append((message, text_color))


@pytest.fixture
def service():
    return VaultService()


def test_generator_guarantees_every_enabled_category(service):
    for _ in range(50):
        password = service.generate_random_password(length=4)

        assert len(password) == 4
        assert any(character in string.ascii_lowercase for character in password)
        assert any(character in string.ascii_uppercase for character in password)
        assert any(character in string.digits for character in password)
        assert any(character in service.PASSWORD_SYMBOLS for character in password)


def test_generator_validates_length_and_type(service):
    with pytest.raises(ValueError, match="too short"):
        service.generate_random_password(length=3)

    with pytest.raises(TypeError, match="integer"):
        service.generate_random_password(length=8.5)


def test_generator_supports_lowercase_only_minimum(service):
    password = service.generate_random_password(
        length=1,
        use_upper=False,
        use_digits=False,
        use_symbols=False,
    )

    assert password in string.ascii_lowercase


@pytest.mark.parametrize(
    ("password", "expected_fragment"),
    [
        ("Short7!", "at least 12"),
        ("qwertyuiop12", "too common"),
        ("AAAAAAAAAAAA", "same character"),
        ("onlylowercasepassword", "three types"),
    ],
)
def test_master_password_policy_rejects_weak_values(
    service,
    password,
    expected_fragment,
):
    is_valid, message = service.validate_master_password(password)

    assert not is_valid
    assert expected_fragment in message


def test_master_password_policy_accepts_strong_value(service):
    is_valid, message = service.validate_master_password(
        "Correct-Horse7"
    )

    assert is_valid
    assert message == ""


def test_legacy_and_duplicate_entries_receive_unique_ids_without_mutation(
    service,
):
    original = [
        {"id": "existing-id", "site": "Same", "password": "secret"},
        {"id": "existing-id", "site": "Same", "password": "secret"},
        {"site": "Legacy", "password": "old"},
    ]

    prepared = service.ensure_entry_ids(original)
    prepared_ids = [item["id"] for item in prepared]

    assert len(set(prepared_ids)) == len(prepared_ids)
    assert prepared[0]["id"] == "existing-id"
    assert prepared[1]["id"] != "existing-id"
    assert "id" not in original[2]


def test_stable_id_finds_the_intended_equal_record(service):
    entries = [
        {"id": "first", "site": "Same", "password": "secret"},
        {"id": "second", "site": "Same", "password": "secret"},
    ]

    assert service.find_entry_index(entries, "second") == 1
    with pytest.raises(ValueError, match="no longer exists"):
        service.find_entry_index(entries, "missing")


def test_clipboard_cleanup_clears_unchanged_owned_secret():
    clipboard = ClipboardStub("vault-secret", "vault-secret")

    cleared = SecureVaultApp.clear_sensitive_clipboard(
        clipboard,
        silent=False,
    )

    assert cleared
    assert clipboard.current_clipboard == ""
    assert clipboard.clear_count == 1
    assert clipboard.cancelled_timers == ["timer-id"]
    assert clipboard.clipboard_timer is None
    assert clipboard.copied_password_value is None
    assert clipboard.toast_messages


def test_clipboard_cleanup_preserves_newer_user_content():
    clipboard = ClipboardStub("vault-secret", "newer copied text")

    cleared = SecureVaultApp.clear_sensitive_clipboard(
        clipboard,
        silent=True,
    )

    assert not cleared
    assert clipboard.current_clipboard == "newer copied text"
    assert clipboard.clear_count == 0
    assert clipboard.cancelled_timers == ["timer-id"]
    assert clipboard.clipboard_timer is None
    assert clipboard.copied_password_value is None
