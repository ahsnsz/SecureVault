# 1. This section is used to set up and verify the test environment, ensuring that all necessary libraries are properly installed and version compatible.
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



# 2. This section is used to start the entire application, create a VaultService instance, and pass it to the GUI layer's AppUI to launch the interface.
from app.bll.vault_service import VaultService
# Test case app.gui.app_ui_test
from app.gui.app_ui import SecureVaultApp


def main():
    # 1. Initialize the Business Logic Layer (BLL)
    service = VaultService()

    # 2. Initialize the GUI layer and pass the Business Logic Layer to it
    # This way buttons in the interface can command the BLL to work
    app = SecureVaultApp(vault_service=service)

    # 3. Start the main loop of the interface
    app.mainloop()


if __name__ == "__main__":
    main()