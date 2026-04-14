import unittest

# Import the core business logic layer (assuming the path is app.bll.vault_service)
from app.bll.vault_service import VaultService


class TestSecureVaultCore(unittest.TestCase):

    def setUp(self):
        """
        setUp runs automatically before each test.
        We initialize a coordinator (VaultService) here for the following tests.
        (If VaultService in your code requires a crypto_manager, pass None or a mock object.)
        """
        try:
            self.service = VaultService()
        except TypeError:
            # Compatibility handling: if VaultService must receive a CryptoManager
            from app.dal.crypto_manager import CryptoManager
            self.service = VaultService(CryptoManager())

    # =====================================
    # Test Suite 1: Password Generator
    # =====================================
    def test_generate_password_length(self):
        """Test 1: Check whether the generated password length is correct."""
        length_to_test = 16
        pwd = self.service.generate_random_password(length=length_to_test)

        # Assert: the expected length of pwd is 16
        self.assertEqual(len(pwd), length_to_test, "Generated password length does not match the expectation")

    def test_generate_password_complexity(self):
        """Test 2: Check whether the generated password contains multiple character types."""
        pwd = self.service.generate_random_password(length=20)

        has_upper = any(c.isupper() for c in pwd)
        has_lower = any(c.islower() for c in pwd)
        has_digit = any(c.isdigit() for c in pwd)

        # Assert: it must contain uppercase, lowercase, and digits
        self.assertTrue(has_upper, "Password is missing an uppercase letter")
        self.assertTrue(has_lower, "Password is missing a lowercase letter")
        self.assertTrue(has_digit, "Password is missing a digit")

    # =====================================
    # Test Suite 2: Strength Evaluator
    # =====================================
    def test_evaluate_strength_weak(self):
        """Test 3: Check whether a very short / numeric-only password is identified as Weak."""
        text, color, progress = self.service.evaluate_password_strength("123")

        self.assertEqual(text, "Weak")
        self.assertEqual(progress, 0.33)

    def test_evaluate_strength_medium(self):
        """Test 4: Check whether a regular password is identified as Medium."""
        text, color, progress = self.service.evaluate_password_strength("Password123")

        self.assertEqual(text, "Medium")
        self.assertEqual(progress, 0.66)

    def test_evaluate_strength_strong(self):
        """Test 5: Check whether a complex password is identified as Strong."""
        text, color, progress = self.service.evaluate_password_strength("My$ecretP@ssw0rd!")

        self.assertEqual(text, "Strong")
        self.assertEqual(progress, 1.0)
        self.assertEqual(color, "#5cb85c")  # Expected to be green

    def test_evaluate_strength_empty(self):
        """Test 6: Check the edge case of an empty password."""
        text, color, progress = self.service.evaluate_password_strength("")

        self.assertEqual(text, "")
        self.assertEqual(progress, 0.0)


if __name__ == '__main__':
    # This line allows us to run this file directly to start the tests
    unittest.main()
