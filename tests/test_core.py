import unittest

# 导入你的核心业务逻辑层 (假设路径是 app.bll.vault_service)
from app.bll.vault_service import VaultService


class TestSecureVaultCore(unittest.TestCase):

    def setUp(self):
        """
        setUp 是每次测试前都会自动运行的准备工作。
        我们在这里初始化一个大堂经理 (VaultService) 供后续测试使用。
        (如果在你的代码里 VaultService 需要传入 crypto_manager，请传入 None 或模拟对象)
        """
        try:
            self.service = VaultService()
        except TypeError:
            # 兼容处理：如果你的 VaultService 必须传入 CryptoManager
            from app.dal.crypto_manager import CryptoManager
            self.service = VaultService(CryptoManager())

    # ==========================================
    # 测试套件 1: 密码生成器 (Password Generator)
    # ==========================================
    def test_generate_password_length(self):
        """测试 1: 检查生成的密码长度是否准确"""
        length_to_test = 16
        pwd = self.service.generate_random_password(length=length_to_test)

        # 断言 (Assert): 期望 pwd 的长度等于 16
        self.assertEqual(len(pwd), length_to_test, "生成的密码长度不符合预期")

    def test_generate_password_complexity(self):
        """测试 2: 检查生成的密码是否包含多种字符类型"""
        pwd = self.service.generate_random_password(length=20)

        has_upper = any(c.isupper() for c in pwd)
        has_lower = any(c.islower() for c in pwd)
        has_digit = any(c.isdigit() for c in pwd)

        # 断言: 必须同时包含大写、小写和数字
        self.assertTrue(has_upper, "密码中缺少大写字母")
        self.assertTrue(has_lower, "密码中缺少小写字母")
        self.assertTrue(has_digit, "密码中缺少数字")

    # ==========================================
    # 测试套件 2: 密码强度评估 (Strength Evaluator)
    # ==========================================
    def test_evaluate_strength_weak(self):
        """测试 3: 检查极短/纯数字密码是否被识别为 Weak"""
        text, color, progress = self.service.evaluate_password_strength("123")

        self.assertEqual(text, "Weak")
        self.assertEqual(progress, 0.33)

    def test_evaluate_strength_medium(self):
        """测试 4: 检查普通密码是否被识别为 Medium"""
        text, color, progress = self.service.evaluate_password_strength("Password123")

        self.assertEqual(text, "Medium")
        self.assertEqual(progress, 0.66)

    def test_evaluate_strength_strong(self):
        """测试 5: 检查复杂密码是否被识别为 Strong"""
        text, color, progress = self.service.evaluate_password_strength("My$ecretP@ssw0rd!")

        self.assertEqual(text, "Strong")
        self.assertEqual(progress, 1.0)
        self.assertEqual(color, "#5cb85c")  # 期望是绿色

    def test_evaluate_strength_empty(self):
        """测试 6: 检查空密码的边界情况 (Edge Case)"""
        text, color, progress = self.service.evaluate_password_strength("")

        self.assertEqual(text, "")
        self.assertEqual(progress, 0.0)


if __name__ == '__main__':
    # 这一行让我们可以直接运行这个文件来启动测试
    unittest.main()