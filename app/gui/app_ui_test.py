import customtkinter as ctk

# 设置整体的主题和颜色风格
ctk.set_appearance_mode("System")  # 跟随系统主题 (深色/浅色)
ctk.set_default_color_theme("blue")  # 蓝色主题


class SecureVaultApp(ctk.CTk):
    """
    Presentation Layer (GUI).
    负责所有的用户界面展示和交互。
    """

    def __init__(self, vault_service):
        super().__init__()

        # 接收传入的业务逻辑服务 (BLL)
        self.vault_service = vault_service

        # 1. 窗口基础设置
        self.title("SecureVault")
        self.geometry("400x500")
        self.resizable(False, False)  # 固定窗口大小，防止布局乱掉

        # 2. 构建登录界面
        self.build_login_screen()

    def build_login_screen(self):
        """构建 Proposal 上的 'Unlock Vault' 界面"""
        # 主框架，让内容居中并留出边距
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(pady=40, padx=40, fill="both", expand=True)

        # 标题 (对应 Mockup 上的 SecureVault)
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="SecureVault",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(0, 10))

        # 副标题
        self.subtitle_label = ctk.CTkLabel(
            self.main_frame,
            text="Enter your master password\nto unlock your vault",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.subtitle_label.pack(pady=(0, 30))

        # 密码输入框 (对应 Mockup 上的 Master Password)
        self.password_entry = ctk.CTkEntry(
            self.main_frame,
            placeholder_text="Enter your master password",
            show="*",  # 输入时显示星号，保护隐私
            width=250,
            height=40
        )
        self.password_entry.pack(pady=(0, 20))

        # 解锁按钮 (对应 Mockup 上的 Unlock Vault)
        self.unlock_btn = ctk.CTkButton(
            self.main_frame,
            text="Unlock Vault",
            width=250,
            height=40,
            command=self.handle_unlock  # 点击时触发的函数
        )
        self.unlock_btn.pack(pady=(0, 10))

    def handle_unlock(self):
        """处理点击解锁按钮的逻辑"""
        # 获取输入框里的密码
        entered_password = self.password_entry.get()
        print(f"User entered password: {entered_password}")

        # 接下来我们会在这里调用 BLL 的 load_vault 方法来验证密码
        # 目前先打印出来测试按钮是否工作