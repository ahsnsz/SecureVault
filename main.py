#1. 这部分用于开始测试环境的设置和验证，确保所有必要的库都已正确安装，并且版本兼容。
# import customtkinter
# import cryptography
# import argon2
# import sys
#
# def check_environment():
#     print(f"Python Version: {sys.version}")
#     print(f"Cryptography Version: {cryptography.__version__}")
#     print(f"CustomTkinter Version: {customtkinter.__version__}")
#     print("Environment setup is SUCCESSFUL! Ready to build SecureVault.")
#
# if __name__ == "__main__":
#     check_environment()




#2. 这个部分用于测试核心加密功能是否正常工作（AES-256-GCM 加密 和 Argon2id 密钥派生），确保我们可以成功加密和解密数据。
# import pytest
# import os
# import json
# from app.dal.crypto_manager import CryptoManager
#
#
# # 测试夹具：每次测试前自动运行
# @pytest.fixture
# def crypto_manager():
#     return CryptoManager()
#
#
# def test_encrypt_decrypt_success(crypto_manager):
#     """测试正常的加密和解密流程"""
#     password = "StrongMasterPassword123!"
#     secret_data = {
#         "gmail": {"username": "user", "password": "abc"},
#         "bank": {"username": "admin", "password": "123"}
#     }
#
#     # 1. 加密
#     encrypted_blob = crypto_manager.encrypt_data(secret_data, password)
#
#     # 验证生成了 bytes 数据，且长度肯定比原文长（因为加了 salt 和 nonce）
#     assert isinstance(encrypted_blob, bytes)
#     assert len(encrypted_blob) > len(json.dumps(secret_data))
#
#     # 2. 解密
#     decrypted_data = crypto_manager.decrypt_data(encrypted_blob, password)
#
#     # 验证解密后的数据与原始内容一致
#     assert decrypted_data == secret_data
#
#
# def test_wrong_password(crypto_manager):
#     """测试使用错误密码解密 (应失败)"""
#     password = "RightPassword"
#     wrong_password = "WrongPassword"
#     data = {"secret": "value"}
#
#     encrypted_blob = crypto_manager.encrypt_data(data, password)
#
#     # 预期会抛出 ValueError (我们在代码里捕获了 InvalidTag 并转抛为 ValueError)
#     with pytest.raises(ValueError, match="Invalid Password"):
#         crypto_manager.decrypt_data(encrypted_blob, wrong_password)
#
#
# def test_tampered_data(crypto_manager):
#     """测试数据被篡改 (AES-GCM 完整性校验应失败)"""
#     password = "password"
#     data = {"secret": "value"}
#
#     encrypted_blob = crypto_manager.encrypt_data(data, password)
#
#     # 模拟黑客修改了文件的一个字节 (将最后一个字节改掉)
#     tampered_blob = bytearray(encrypted_blob)
#     tampered_blob[-1] = (tampered_blob[-1] + 1) % 256
#
#     # 解密篡改后的数据应报错
#     with pytest.raises(ValueError, match="Invalid Password or Corrupted Data"):
#         crypto_manager.decrypt_data(bytes(tampered_blob), password)




#3. 这个部分用于测试整个应用的核心功能是否正常工作，包括密码生成、数据保存和数据读取。
# import os
# from app.bll.vault_service import VaultService
#
# def main():
#     service = VaultService()
#     test_file = "test_vault.svdb"
#     master_pwd = "MySecretPassword123"
#
#     print("1. 测试生成强密码...")
#     new_pwd = service.generate_random_password(length=16)
#     print(f"生成的密码是: {new_pwd}")
#
#     print("\n2. 测试保存数据...")
#     my_data = [{"site": "Liverpool Canvas", "username": "student", "password": new_pwd}]
#     service.save_vault(test_file, master_pwd, my_data)
#     print(f"数据已加密并保存到 {test_file}")
#
#     print("\n3. 测试读取数据...")
#     loaded_data = service.load_vault(test_file, master_pwd)
#     print(f"成功解密读取数据: {loaded_data}")
#
#     # 测试完后清理现场
#     if os.path.exists(test_file):
#         os.remove(test_file)
#         print("\n测试文件已清理。")
#
# if __name__ == "__main__":
#     main()





# 4. 这个部分用于启动整个应用，创建 VaultService 实例，并将其传递给 GUI 层的 AppUI 来启动界面。
from app.bll.vault_service import VaultService
# 测试用例 app.gui.app_ui_test
from app.gui.app_ui import SecureVaultApp


def main():
    # 1. 初始化业务逻辑层 (大堂经理)
    service = VaultService()

    # 2. 初始化 GUI 层，并把业务逻辑层传给它
    # 这样界面里的按钮就能指挥大堂经理干活了
    app = SecureVaultApp(vault_service=service)

    # 3. 启动界面的主循环
    app.mainloop()


if __name__ == "__main__":
    main()