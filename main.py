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



# 2. 这个部分用于启动整个应用，创建 VaultService 实例，并将其传递给 GUI 层的 AppUI 来启动界面。
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