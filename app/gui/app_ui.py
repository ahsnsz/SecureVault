import os
import json # <--- 新增用于读写历史记录
from tkinter import filedialog  # <--- 新增用于调出系统的文件选择窗口
import csv  # <--- 新增这行，用于处理 Excel/CSV 表格格式
import customtkinter as ctk

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

import os
import json
from tkinter import filedialog
import customtkinter as ctk



# ==========================================
# 自定义 ToolTip 悬浮提示小组件
# ==========================================
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        # 绑定鼠标进入和离开事件
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        """鼠标悬停时显示提示框"""
        # 计算悬浮窗的位置（在按钮的右下方一点）
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        # 创建一个没有边框的顶层窗口
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)  # 去除 macOS 窗口的标题栏和控制按钮
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # 悬浮窗里的文本标签 (深灰色背景，圆角)
        label = ctk.CTkLabel(
            self.tooltip_window,
            text=self.text,
            fg_color=("gray70", "gray30"),
            corner_radius=6,
            padx=10, pady=5,
            font=ctk.CTkFont(size=12)
        )
        label.pack()

    def hide_tooltip(self, event=None):
        """鼠标离开时销毁提示框"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None




class SecureVaultApp(ctk.CTk):
    def __init__(self, vault_service):
        super().__init__()
        self.vault_service = vault_service

        # ====== 修复打包后的只读报错：设置安全的绝对路径 ======
        # 获取当前电脑用户的“文稿 (Documents)”目录
        self.user_docs_dir = os.path.join(os.path.expanduser("~"), "Documents", "SecureVault_Data")

        # 如果这个文件夹不存在，就自动创建它
        if not os.path.exists(self.user_docs_dir):
            os.makedirs(self.user_docs_dir)

        # 把默认的数据库和配置文件，全都塞进这个安全的文件夹里
        default_vault = os.path.join(self.user_docs_dir, "my_vault.svdb")
        self.recent_json_path = os.path.join(self.user_docs_dir, "recent_vaults.json")
        # =======================================================

        self.vault_filepath = default_vault  # 使用新的安全默认路径
        self.vault_data = []
        self.master_password = ""  # 初始化为空

        self.title("SecureVault")
        self.geometry("400x500")
        self.resizable(False, False)

        # --- 新增：自动锁定定时器相关变量 ---
        self.inactivity_timer = None
        # 【注意】为了方便你马上看到效果，这里我先设置成 5 秒 (5000毫秒)。
        # 测试成功后，在写论文前，请把它改成 300000 (即 5 分钟)。
        self.timeout_ms = 300000
        self.setup_inactivity_tracker()

        self.build_login_screen()


    def get_recent_vaults(self):
        """读取最近使用的金库路径"""
        # 替换为新的绝对路径变量
        if os.path.exists(self.recent_json_path):
            try:
                with open(self.recent_json_path, "r") as f:
                    return json.load(f)
            except:
                pass
        return []

    def add_recent_vault(self, filepath):
        """将成功打开的金库添加到历史记录，并最多保留 5 个"""
        recents = self.get_recent_vaults()
        if filepath in recents:
            recents.remove(filepath)
        recents.insert(0, filepath)
        recents = recents[:5]

        # 替换为新的绝对路径变量
        with open(self.recent_json_path, "w") as f:
            json.dump(recents, f)


    def setup_inactivity_tracker(self):
        """监听全局的鼠标和键盘事件 (对应 Proposal Req 27)"""
        # 只要键盘按键、鼠标点击、或者鼠标移动，就触发 reset_timer
        self.bind_all("<Any-KeyPress>", self.reset_timer)
        self.bind_all("<Any-ButtonPress>", self.reset_timer)
        self.bind_all("<Motion>", self.reset_timer)
        self.reset_timer()  # 启动初始倒计时


    def reset_timer(self, event=None):
        """每次用户有操作时，打断旧的倒计时，重新开始计时"""
        if self.inactivity_timer:
            # 取消之前设定的闹钟
            self.after_cancel(self.inactivity_timer)
        # 设定一个新闹钟，时间到了就执行 self.lock_vault
        self.inactivity_timer = self.after(self.timeout_ms, self.lock_vault)


    def lock_vault(self):
        """时间到！锁定程序，清除内存数据，退回登录界面"""
        # 检查：如果当前已经在登录界面（没有 sidebar_frame），就不用重复锁了
        if not hasattr(self, 'sidebar_frame') or not self.sidebar_frame.winfo_exists():
            return

        # 1. 核心安全步骤：彻底清除内存中的明文数据和主密码！
        self.vault_data = []
        self.master_password = ""

        # 2. 销毁主界面的左右两块区域，防止泄露
        self.sidebar_frame.destroy()
        self.main_content_frame.destroy()

        # 3. 恢复登录窗口的大小
        self.geometry("400x500")

        # 4. 重新构建登录界面
        self.build_login_screen()

        # 5. 给用户一个醒目的橙色提示
        self.status_label.configure(text="Locked due to inactivity.", text_color="#f0ad4e")


    def build_login_screen(self):
        """构建登录界面，包含最近使用的金库列表 (还原 Proposal UI/UX Mockup)"""
        # 调整窗口大小以容纳左侧的 Recent 栏
        self.geometry("650x500")

        # 整个登录界面的大容器
        self.login_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.login_wrapper.pack(fill="both", expand=True)

        # ==========================================
        # 左侧：Recent Vaults (最近金库)
        # ==========================================
        recent_vaults = self.get_recent_vaults()

        self.recent_frame = ctk.CTkFrame(self.login_wrapper, width=200, fg_color=("gray90", "gray13"))
        self.recent_frame.pack(side="left", fill="y", padx=20, pady=40)

        ctk.CTkLabel(self.recent_frame, text="Recent Vaults", font=ctk.CTkFont(size=16, weight="bold")).pack(
            pady=(20, 10), padx=20)

        if not recent_vaults:
            ctk.CTkLabel(self.recent_frame, text="No recent vaults.", text_color="gray").pack(pady=10)
        else:
            for path in recent_vaults:
                filename = os.path.basename(path)
                btn = ctk.CTkButton(
                    self.recent_frame, text=f"📄 {filename}",
                    fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                    anchor="w", width=160,
                    # 点击历史记录，直接选中该文件
                    command=lambda p=path: self._update_filepath_ui(p)
                )
                btn.pack(pady=5, padx=10)

        # ==========================================
        # 右侧：主登录表单
        # ==========================================
        self.login_frame = ctk.CTkFrame(self.login_wrapper, fg_color="transparent")
        self.login_frame.pack(side="left", fill="both", expand=True, pady=40, padx=(0, 20))

        self.title_label = ctk.CTkLabel(self.login_frame, text="SecureVault", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=(0, 10))

        file_display_name = os.path.basename(self.vault_filepath) if self.vault_filepath else "No vault selected"
        self.file_label = ctk.CTkLabel(self.login_frame, text=f"Selected Vault: {file_display_name}",
                                       font=ctk.CTkFont(size=13, weight="bold"), text_color="#3a7ebf")
        self.file_label.pack(pady=(0, 5))

        prompt_text = "Enter master password to unlock" if os.path.exists(
            self.vault_filepath) else "Create a master password for new vault"
        self.subtitle_label = ctk.CTkLabel(self.login_frame, text=prompt_text, font=ctk.CTkFont(size=14),
                                           text_color="gray")
        self.subtitle_label.pack(pady=(0, 20))

        self.password_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Master password", show="*", width=250,
                                           height=40)
        self.password_entry.pack(pady=(0, 10))
        self.password_entry.bind("<Return>", self.handle_unlock)

        self.status_label = ctk.CTkLabel(self.login_frame, text="", text_color="red")
        self.status_label.pack(pady=(0, 10))

        self.unlock_btn = ctk.CTkButton(self.login_frame, text="Unlock / Create Vault", width=250, height=40,
                                        command=self.handle_unlock)
        self.unlock_btn.pack(pady=(0, 10))

        db_btn_frame = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        db_btn_frame.pack(pady=(15, 0))

        self.open_db_btn = ctk.CTkButton(db_btn_frame, text="📂 Open Vault", width=120, height=35,
                                         fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
                                         command=self.handle_open_file)
        self.open_db_btn.pack(side="left", padx=(0, 5))

        self.new_db_btn = ctk.CTkButton(db_btn_frame, text="➕ New Vault", width=120, height=35, fg_color="transparent",
                                        border_width=1, text_color=("gray10", "gray90"), command=self.handle_new_file)
        self.new_db_btn.pack(side="left", padx=(5, 0))


    def handle_open_file(self):
        """打开系统文件对话框，让用户选择已存在的文件 (askopenfilename 不会变灰)"""
        filepath = filedialog.askopenfilename(
            title="Open Existing Vault",
            filetypes=[("SecureVault Database", "*.svdb"), ("All Files", "*.*")]
        )
        if filepath:
            self._update_filepath_ui(filepath)


    def handle_new_file(self):
        """打开系统文件对话框，让用户保存新文件 (asksaveasfilename)"""
        filepath = filedialog.asksaveasfilename(
            title="Create New Vault",
            defaultextension=".svdb",
            filetypes=[("SecureVault Database", "*.svdb"), ("All Files", "*.*")]
        )
        if filepath:
            self._update_filepath_ui(filepath)


    def _update_filepath_ui(self, filepath):
        """内部方法：统一处理选中文件后的界面更新逻辑"""
        self.vault_filepath = filepath

        file_display_name = os.path.basename(self.vault_filepath)
        self.file_label.configure(text=f"Selected Vault: {file_display_name}")

        prompt_text = "Enter master password to unlock" if os.path.exists(
            self.vault_filepath) else "Create a master password for new vault"
        self.subtitle_label.configure(text=prompt_text)

        self.password_entry.delete(0, 'end')
        self.status_label.configure(text="")


    def handle_unlock(self, event=None):
        """核心逻辑：处理点击按钮后的加解密请求"""
        password = self.password_entry.get()

        # 将用户输入的密码保存到实例属性中，让程序记住密码以便后续使用（记住主密码是为了在“保存新数据”时，能够重新给文件加密）
        self.master_password = password

        if not password:
            self.status_label.configure(text="Password cannot be empty!", text_color="red")
            return

        # 场景 1：如果金库文件不存在，则创建新金库
        if not os.path.exists(self.vault_filepath):
            try:
                # 呼叫 BLL 创建新金库
                self.vault_data = self.vault_service.create_new_vault(self.vault_filepath, password)
                self.status_label.configure(text="New vault created!", text_color="green")
                # 【新增】：创建成功后，把这个文件路径保存到“最近使用”的历史记录里
                self.add_recent_vault(self.vault_filepath)
                # 延迟 1 秒后进入主界面 (提升用户体验)
                self.after(500, self.show_main_vault_screen)
            except Exception as e:
                self.status_label.configure(text=f"Error: {str(e)}", text_color="red")

        # 场景 2：如果金库文件已存在，则尝试解密
        else:
            try:
                # 呼叫 BLL 读取并解密
                self.vault_data = self.vault_service.load_vault(self.vault_filepath, password)
                self.status_label.configure(text="Unlocked successfully!", text_color="green")
                # 【新增】：创建成功后，把这个文件路径保存到“最近使用”的历史记录里
                self.add_recent_vault(self.vault_filepath)
                # 延迟 1 秒后进入主界面
                self.after(500, self.show_main_vault_screen)
            except ValueError:
                # 这里的 ValueError 是我们在 DAL (crypto_manager) 里抛出的密码错误异常
                self.status_label.configure(text="Invalid password! Try again.", text_color="red")
            except Exception as e:
                self.status_label.configure(text="File corrupted or unknown error.", text_color="red")


    def handle_logout(self):
        """主动锁定金库并返回登录/切换界面"""
        # 确保我们在主界面
        if hasattr(self, 'sidebar_frame') and self.sidebar_frame.winfo_exists():
            # 1. 核心安全步骤：彻底清除内存中的明文数据和主密码！
            self.vault_data = []
            self.master_password = ""

            # 2. 销毁主界面的左右两块区域
            self.sidebar_frame.destroy()
            self.main_content_frame.destroy()

            # 3. 恢复成带左侧历史记录的登录窗口大小
            self.geometry("650x500")

            # 4. 重新构建登录界面
            self.build_login_screen()

            # 5. 给用户一个绿色的安全退出提示
            self.status_label.configure(text="Vault locked successfully. Ready to switch.", text_color="green")


    def show_main_vault_screen(self):
        """进入主密码本界面 (对应 Proposal 的 All Passwords 界面)"""
        # 1. 【修改点】：因为我们在登录界面加了左侧栏，外面包了一层 login_wrapper
        # 所以进入主界面时，必须把这一整层 wrapper 全部销毁，才能清空屏幕
        if hasattr(self, 'login_wrapper') and self.login_wrapper.winfo_exists():
            self.login_wrapper.destroy()

        # 2. 调整窗口大小以适应主界面 (Mockup 显示这是一个宽屏界面)
        self.geometry("900x600")

        # 3. 使用 Grid 布局划分左右两块区域 (0列是侧边栏，1列是主内容)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)  # 让右侧主内容区占据所有的剩余空间

        # ==========================================
        # 左侧：导航侧边栏 (Sidebar)
        # ==========================================
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SecureVault", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # 1. 所有密码选项卡
        self.nav_all_btn = ctk.CTkButton(
            self.sidebar_frame, text="All Passwords", corner_radius=8,
            fg_color="transparent", text_color=("gray10", "gray90"), anchor="w",
            command=self.nav_click_all_passwords  # 绑定到新的高亮切换函数
        )
        self.nav_all_btn.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        # 2. 添加密码选项卡
        self.nav_add_btn = ctk.CTkButton(
            self.sidebar_frame, text="+ Add Password", corner_radius=8,
            fg_color="transparent", text_color=("gray10", "gray90"), anchor="w",
            command=self.nav_click_add_password
        )
        self.nav_add_btn.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        # 3. 设置选项卡 (取代了原本的 Generate 和 Change Password)
        self.nav_settings_btn = ctk.CTkButton(
            self.sidebar_frame, text="⚙️ Settings", corner_radius=8,
            fg_color="transparent", text_color=("gray10", "gray90"), anchor="w",
            command=self.nav_click_settings
        )
        self.nav_settings_btn.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        # 将这三个按钮存入列表，方便后续统一切换颜色
        self.nav_tabs = [self.nav_all_btn, self.nav_add_btn, self.nav_settings_btn]

        # 底部红色的锁定按钮保持不变
        self.nav_lock_btn = ctk.CTkButton(
            self.sidebar_frame, text="🔒 Lock & Switch",
            fg_color="#d9534f", hover_color="#c9302c", anchor="w",
            command=self.handle_logout
        )
        self.nav_lock_btn.grid(row=5, column=0, padx=20, pady=(50, 20), sticky="ew")
        ToolTip(self.nav_lock_btn, "Lock vault and return to login screen")

        # ==========================================
        # 右侧：主内容区 (Main Content)
        # ==========================================
        self.main_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        # 刚进入主界面时，默认模拟点击“所有密码”选项卡 (这样一进来就带有高亮背景)
        self.nav_click_all_passwords()

        # ====== 新增：锁定与切换金库按钮 ======
        self.nav_lock_btn = ctk.CTkButton(
            self.sidebar_frame, text="🔒 Lock & Switch",
            fg_color="#d9534f", hover_color="#c9302c", anchor="w",  # 红色警告色
            command=self.handle_logout  # 绑定到主动退出方法
        )
        # 放在第 5 行，让它靠下一点
        self.nav_lock_btn.grid(row=5, column=0, padx=20, pady=(50, 20), sticky="ew")
        ToolTip(self.nav_lock_btn, "Lock vault and return to login screen")  # 新增

        # ==========================================
        # 右侧：主内容区 (Main Content)
        # ==========================================
        self.main_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        # 刚进入主界面时，默认显示“所有密码”列表
        self.show_password_list()

    def show_password_list(self, search_query=""):
        """在右侧区域显示密码列表，支持搜索过滤 (还原 Proposal Req 6)"""
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()

        # --- 顶部：标题与搜索栏 ---
        header_frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        title = ctk.CTkLabel(header_frame, text="All Passwords", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(side="left")

        # 搜索输入框
        search_entry = ctk.CTkEntry(header_frame, placeholder_text="Search site or user...", width=200)
        search_entry.pack(side="right", padx=(10, 0))
        if search_query:
            search_entry.insert(0, search_query)  # 如果有搜索词，保持显示在框里

        # 触发搜索的内部函数
        def perform_search(*args):
            query = search_entry.get()
            self.show_password_list(search_query=query)

        # 绑定回车键触发搜索
        search_entry.bind("<Return>", perform_search)

        search_btn = ctk.CTkButton(header_frame, text="Search", width=60, command=perform_search)
        search_btn.pack(side="right")

        self.list_status_label = ctk.CTkLabel(header_frame, text="", text_color="green")
        self.list_status_label.pack(side="right", padx=20)

        # --- 列表区域 ---
        list_frame = ctk.CTkScrollableFrame(self.main_content_frame, fg_color="transparent")
        list_frame.pack(fill="both", expand=True)

        # 根据搜索词过滤数据 (忽略大小写)
        filtered_data = []
        for item in self.vault_data:
            site = item.get("site", "").lower()
            user = item.get("username", "").lower()
            query = search_query.lower()
            if query in site or query in user:
                filtered_data.append(item)

        if not filtered_data:
            empty_text = "No passwords found matching your search." if search_query else "Your vault is empty.\nClick '+ Add Password' to get started."
            ctk.CTkLabel(list_frame, text=empty_text, text_color="gray").pack(pady=100)
            return

        # 渲染过滤后的卡片
        for item in filtered_data:
            card = ctk.CTkFrame(list_frame, corner_radius=8)
            card.pack(fill="x", pady=5, padx=5)

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", padx=15, pady=10, fill="x", expand=True)

            site_name = item.get("site", "Unknown")
            ctk.CTkLabel(info_frame, text=site_name, font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")

            account_info = item.get("username", "")
            email = item.get("email", "")
            if email:
                account_info += f" ({email})" if account_info else email

            if account_info:
                ctk.CTkLabel(info_frame, text=account_info, text_color="gray", font=ctk.CTkFont(size=12)).pack(
                    anchor="w")

            # 红色删除按钮
            # 找到当前 item 在原始 vault_data 中的真实索引
            real_index = self.vault_data.index(item)
            delete_btn = ctk.CTkButton(
                card, text="Delete", width=60, fg_color="#d9534f", hover_color="#c9302c",
                command=lambda idx=real_index: self.delete_password(idx)
            )
            delete_btn.pack(side="right", padx=(0, 15))
            ToolTip(delete_btn, "Permanently delete this entry")  # 新增

            # --- 新增：橙色编辑按钮 ---
            edit_btn = ctk.CTkButton(
                card, text="Edit", width=60, fg_color="#f0ad4e", hover_color="#ec971f", text_color="black",
                # 点击时，把这条数据的索引 (idx) 和具体内容 (itm) 传给编辑表单
                command=lambda idx=real_index, itm=item: self.show_edit_password_form(idx, itm)
            )
            edit_btn.pack(side="right", padx=(0, 10))
            ToolTip(edit_btn, "Edit this password entry")  # 新增

            # 复制密码按钮
            copy_btn = ctk.CTkButton(
                card, text="Copy", width=60,
                command=lambda pwd=item.get("password"), site=site_name: self.copy_to_clipboard(pwd, site)
            )
            copy_btn.pack(side="right", padx=(0, 10))
            ToolTip(copy_btn, "Copy password to clipboard")  # 新增


    def show_edit_password_form(self, index, item):
        """显示编辑表单，并预先填入该条密码的旧数据 (还原 Proposal Req 5)"""
        # 清空右侧内容区
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()

        title = ctk.CTkLabel(self.main_content_frame, text="Edit Password", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(anchor="w", pady=(0, 20))

        form_frame = ctk.CTkScrollableFrame(self.main_content_frame, fg_color="transparent")
        form_frame.pack(fill="both", expand=True)

        # 1. 网站名称 (预填旧数据)
        ctk.CTkLabel(form_frame, text="Website/Service Name *").pack(anchor="w", pady=(10, 0))
        self.edit_entry_site = ctk.CTkEntry(form_frame, width=400)
        self.edit_entry_site.insert(0, item.get("site", ""))  # 插入旧数据
        self.edit_entry_site.pack(anchor="w", pady=(0, 10))

        # 2. 用户名
        ctk.CTkLabel(form_frame, text="Username").pack(anchor="w", pady=(10, 0))
        self.edit_entry_username = ctk.CTkEntry(form_frame, width=400)
        self.edit_entry_username.insert(0, item.get("username", ""))
        self.edit_entry_username.pack(anchor="w", pady=(0, 10))

        # 3. 邮箱
        ctk.CTkLabel(form_frame, text="Email Address").pack(anchor="w", pady=(10, 0))
        self.edit_entry_email = ctk.CTkEntry(form_frame, width=400)
        self.edit_entry_email.insert(0, item.get("email", ""))
        self.edit_entry_email.pack(anchor="w", pady=(0, 10))

        # 4. 密码
        ctk.CTkLabel(form_frame, text="Password *").pack(anchor="w", pady=(10, 0))
        pwd_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        pwd_frame.pack(anchor="w", fill="x")

        # 密码输入框 (宽度缩减为240)
        self.edit_entry_password = ctk.CTkEntry(pwd_frame, show="*", width=240)
        self.edit_entry_password.insert(0, item.get("password", ""))
        self.edit_entry_password.pack(side="left", padx=(0, 5))

        # --- 新增：Edit 界面的小眼睛按钮 ---
        self.btn_show_edit_pwd = ctk.CTkButton(
            pwd_frame, text="👁️", width=30, fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
            command=lambda: self.toggle_password_visibility(self.edit_entry_password, self.btn_show_edit_pwd)
        )
        self.btn_show_edit_pwd.pack(side="left", padx=(0, 10))
        ToolTip(self.btn_show_edit_pwd, "Show/Hide Password")
        # -----------------------------------

        # 生成新密码按钮
        btn_generate = ctk.CTkButton(pwd_frame, text="Generate New", width=110,
                                     command=self.handle_generate_edit_password)
        btn_generate.pack(side="left")
        ToolTip(btn_generate, "Generate a new secure password")

        self.edit_status_label = ctk.CTkLabel(form_frame, text="", text_color="red")
        self.edit_status_label.pack(anchor="w", pady=(10, 0))

        # 5. 操作按钮区
        btn_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=(20, 0))

        # 保存修改
        btn_save = ctk.CTkButton(btn_frame, text="Save Changes", command=lambda: self.handle_update_password(index))
        btn_save.pack(side="left", padx=(0, 10))

        # 取消修改，返回列表
        btn_cancel = ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", hover_color="#555555",
                                   command=self.show_password_list)
        btn_cancel.pack(side="left")

    def handle_generate_edit_password(self):
        """在编辑表单中生成新密码"""
        new_pwd = self.vault_service.generate_random_password(length=16)
        self.edit_entry_password.delete(0, 'end')
        self.edit_entry_password.insert(0, new_pwd)
        self.edit_entry_password.configure(show="")

        # --- 新增：同步更新小眼睛的图标 ---
        if hasattr(self, 'btn_show_edit_pwd') and self.btn_show_edit_pwd.winfo_exists():
            self.btn_show_edit_pwd.configure(text="🙈")

    def handle_update_password(self, index):
        """收集修改后的数据，覆盖旧数据，并重新加密保存"""
        site = self.edit_entry_site.get().strip()
        username = self.edit_entry_username.get().strip()
        email = self.edit_entry_email.get().strip()
        password = self.edit_entry_password.get()

        if not site or not password:
            self.edit_status_label.configure(text="Website and Password are required!", text_color="red")
            return

        # 1. 更新内存中指定索引的数据
        self.vault_data[index] = {
            "site": site,
            "username": username,
            "email": email,
            "password": password
        }

        try:
            # 2. 呼叫大堂经理，用主密码重新加密整个列表，写入硬盘
            self.vault_service.save_vault(self.vault_filepath, self.master_password, self.vault_data)

            # 3. 保存成功后，自动跳回密码列表界面
            self.show_password_list()

            # 4. 在列表页顶部显示绿色的成功提示
            self.list_status_label.configure(text=f"'{site}' updated successfully!", text_color="green")
            self.after(3000, lambda: self.list_status_label.configure(text=""))
        except Exception as e:
            self.edit_status_label.configure(text=f"Update failed: {e}", text_color="red")


    def delete_password(self, index):
        """删除指定密码并重新加密保存 """
        deleted_item = self.vault_data.pop(index)  # 从内存中移除

        try:
            # 呼叫 BLL：用剩下的数据覆盖硬盘里的旧文件
            self.vault_service.save_vault(self.vault_filepath, self.master_password, self.vault_data)
            # 重新刷新列表界面
            self.show_password_list()
            self.list_status_label.configure(text=f"'{deleted_item.get('site')}' deleted!", text_color="red")
            self.after(3000, lambda: self.list_status_label.configure(text=""))
        except Exception as e:
            self.list_status_label.configure(text=f"Delete failed: {e}", text_color="red")


    def copy_to_clipboard(self, password, site_name):
        """将密码复制到系统剪贴板，并启动 '阅后即焚' 倒计时"""
        # 1. 执行复制
        self.clipboard_clear()
        self.clipboard_append(password)
        self.update()

        # 2. 更新提示语，告知用户有时间限制
        self.show_toast(f"Password for '{site_name}' copied! (Clears in 30s)", text_color="#5cb85c") # 绿色

        # 3. 阅后即焚逻辑：如果之前用户已经复制过其他密码，先取消旧的倒计时
        if hasattr(self, 'clipboard_timer') and self.clipboard_timer:
            self.after_cancel(self.clipboard_timer)

        # 4. 设定一个 30 秒 (30000毫秒) 的新倒计时，时间到了就执行清空
        self.clipboard_timer = self.after(30000, self.auto_clear_clipboard)

    def auto_clear_clipboard(self):
        """时间到！强制清空系统剪贴板，防止密码泄露"""
        self.clipboard_clear()
        self.clipboard_append("")  # <--- 【关键修复】：强制写入一个空字符，彻底覆盖掉操作系统的底层剪贴板
        self.update()  # 推送到操作系统

        self.clipboard_timer = None

        # 如果用户目前还停留在密码列表界面，给一个橙色的安全提示
        self.show_toast("Clipboard auto-cleared for security.", text_color="#f0ad4e") # 橙色


    def show_add_password_form(self):
        """在右侧区域显示添加密码的表单，包含密码强度检测"""
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()

        title = ctk.CTkLabel(self.main_content_frame, text="Add New Password", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(anchor="w", pady=(0, 20))

        form_frame = ctk.CTkScrollableFrame(self.main_content_frame, fg_color="transparent")
        form_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(form_frame, text="Website/Service Name *").pack(anchor="w", pady=(10, 0))
        self.entry_site = ctk.CTkEntry(form_frame, placeholder_text="e.g., Gmail, Facebook, Amazon", width=400)
        self.entry_site.pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(form_frame, text="Username").pack(anchor="w", pady=(10, 0))
        self.entry_username = ctk.CTkEntry(form_frame, placeholder_text="Enter username", width=400)
        self.entry_username.pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(form_frame, text="Email Address").pack(anchor="w", pady=(10, 0))
        self.entry_email = ctk.CTkEntry(form_frame, placeholder_text="Enter email address", width=400)
        self.entry_email.pack(anchor="w", pady=(0, 10))

        # 4. Password (包含输入框、小眼睛 和 Generate 按钮)
        ctk.CTkLabel(form_frame, text="Password *").pack(anchor="w", pady=(10, 0))

        pwd_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        pwd_frame.pack(anchor="w", fill="x")

        # 密码输入框 (宽度从280稍微缩减到240)
        self.entry_password = ctk.CTkEntry(pwd_frame, placeholder_text="Enter or generate password", show="*",
                                           width=240)
        self.entry_password.pack(side="left", padx=(0, 5))

        # --- 新增：小眼睛按钮 ---
        self.btn_show_pwd = ctk.CTkButton(
            pwd_frame, text="👁️", width=30, fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
            command=lambda: self.toggle_password_visibility(self.entry_password, self.btn_show_pwd)
        )
        self.btn_show_pwd.pack(side="left", padx=(0, 10))
        ToolTip(self.btn_show_pwd, "Show/Hide Password")  # 挂上刚才做的 Tooltip
        # -------------------------

        # 绑定键盘松开事件：每次输入一个字符，就去检测一次强度
        self.entry_password.bind("<KeyRelease>", self.update_password_strength)

        btn_generate = ctk.CTkButton(pwd_frame, text="Generate", width=110, command=self.handle_generate_password)
        btn_generate.pack(side="left")

        # --- 新增这行：贴上悬浮提示 ---
        ToolTip(btn_generate, "Click to generate a 16-character secure password")

        # --- 新增：密码强度显示标签 ---
        # --- 华丽升级：密码强度进度条区域 ---
        self.strength_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        self.strength_frame.pack(anchor="w", pady=(10, 0), fill="x")

        # 进度条前面的提示文字
        ctk.CTkLabel(self.strength_frame, text="Strength: ", font=ctk.CTkFont(size=12)).pack(side="left")

        # 核心组件：进度条
        self.strength_progressbar = ctk.CTkProgressBar(self.strength_frame, width=150, height=8)
        self.strength_progressbar.pack(side="left", padx=(5, 10))
        self.strength_progressbar.set(0)  # 初始进度为 0

        # 进度条后面的状态文字 (Weak/Medium/Strong)
        self.strength_label = ctk.CTkLabel(self.strength_frame, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.strength_label.pack(side="left")

        self.add_status_label = ctk.CTkLabel(form_frame, text="", text_color="red")
        self.add_status_label.pack(anchor="w", pady=(10, 0))

        btn_save = ctk.CTkButton(form_frame, text="Save Password", command=self.handle_save_password)
        btn_save.pack(anchor="w", pady=(20, 0))


    def update_password_strength(self, event=None):
        """实时更新密码强度显示和进度条"""
        current_pwd = self.entry_password.get()
        # 接收 BLL 传回的三个参数：文字、颜色、进度值
        strength_text, color, progress_value = self.vault_service.evaluate_password_strength(current_pwd)

        if strength_text:
            # 更新文字
            self.strength_label.configure(text=strength_text, text_color=color)
            # 更新进度条颜色和长度
            self.strength_progressbar.configure(progress_color=color)
            self.strength_progressbar.set(progress_value)
        else:
            # 如果密码框清空了，恢复默认状态
            self.strength_label.configure(text="")
            self.strength_progressbar.set(0)
            self.strength_progressbar.configure(progress_color="gray")


    def handle_generate_password(self):
        """点击 Generate 按钮触发：呼叫 BLL 生成密码并显示"""
        # 1. 生成新密码
        new_pwd = self.vault_service.generate_random_password(length=16)

        # 2. 清空密码框，填入新密码
        self.entry_password.delete(0, 'end')
        self.entry_password.insert(0, new_pwd)

        # 3. 取消星号遮挡
        self.entry_password.configure(show="")

        # 【关键修复】：因为代码填入密码不会触发物理键盘事件，必须手动强制更新一次！
        self.update_password_strength()

        # --- 新增：同步更新小眼睛的图标 ---
        if hasattr(self, 'btn_show_pwd') and self.btn_show_pwd.winfo_exists():
            self.btn_show_pwd.configure(text="🙈")


    def handle_save_password(self):
        """点击 Save 按钮触发：收集数据，加密保存到本地"""
        site = self.entry_site.get().strip()
        username = self.entry_username.get().strip()
        email = self.entry_email.get().strip()
        password = self.entry_password.get()

        # 简单验证：网站和密码不能为空
        if not site or not password:
            self.add_status_label.configure(text="Website and Password are required!", text_color="red")
            return

        # 1. 组装成一个字典
        new_entry = {
            "site": site,
            "username": username,
            "email": email,
            "password": password
        }

        # 2. 追加到内存中的数据列表
        self.vault_data.append(new_entry)

        try:
            # 3. 呼叫大堂经理 (BLL)，用刚才记住的 master_password 重新加密写入硬盘
            self.vault_service.save_vault(self.vault_filepath, self.master_password, self.vault_data)
            self.add_status_label.configure(text=f"'{site}' saved successfully!", text_color="green")

            # 清空表单，方便录入下一个
            self.entry_site.delete(0, 'end')
            self.entry_username.delete(0, 'end')
            self.entry_email.delete(0, 'end')
            self.entry_password.delete(0, 'end')
            self.entry_password.configure(show="*")  # 恢复星号遮挡

        except Exception as e:
            self.add_status_label.configure(text=f"Save failed: {e}", text_color="red")


    def toggle_password_visibility(self, entry_widget, button_widget):
        """通用方法：切换密码框的明文/星号显示，并更换按钮图标"""
        if entry_widget.cget("show") == "*":
            # 如果当前是隐藏状态，则改为显示，并换成“闭眼/猴子”图标
            entry_widget.configure(show="")
            button_widget.configure(text="👁️")
        else:
            # 如果当前是显示状态，则改为隐藏，换成“睁眼”图标
            entry_widget.configure(show="*")
            button_widget.configure(text="🙈")


    def handle_change_master_password(self):
        """处理修改主密码的逻辑：验证身份 -> 重新加密 -> 覆盖文件"""
        old_pwd = self.entry_old_master.get()
        new_pwd = self.entry_new_master.get()
        confirm_pwd = self.entry_confirm_master.get()

        # 1. 基础非空校验
        if not old_pwd or not new_pwd or not confirm_pwd:
            self.change_pwd_status.configure(text="All fields are required!", text_color="red")
            return

        # 2. 验证旧密码是否正确（利用我们在解锁时记住的 self.master_password）
        if old_pwd != self.master_password:
            self.change_pwd_status.configure(text="Current password is incorrect!", text_color="red")
            return

        # 3. 验证新密码规则
        if new_pwd == old_pwd:
            self.change_pwd_status.configure(text="New password must be different from the old one!", text_color="red")
            return

        if new_pwd != confirm_pwd:
            self.change_pwd_status.configure(text="New passwords do not match!", text_color="red")
            return

        try:
            # 4. 呼叫大堂经理 (BLL)，用【新密码】重新加密当前的 vault_data，并覆盖保存
            self.vault_service.save_vault(self.vault_filepath, new_pwd, self.vault_data)

            # 5. 非常重要：更新内存中记住的密码，防止后续添加/删除密码时用错旧密码！
            self.master_password = new_pwd

            # 6. 界面反馈
            self.change_pwd_status.configure(text="Master password updated successfully!", text_color="green")

            # 清空输入框
            self.entry_old_master.delete(0, 'end')
            self.entry_new_master.delete(0, 'end')
            self.entry_confirm_master.delete(0, 'end')

        except Exception as e:
            self.change_pwd_status.configure(text=f"Failed to update password: {e}", text_color="red")


    def show_toast(self, message, text_color="white"):
        """在窗口底部中央显示一个悬浮的圆角提示框 (Toast Notification)"""
        # 1. 如果之前已经有一个提示框在显示，先销毁它，防止重叠
        if hasattr(self, 'toast_timer') and self.toast_timer is not None:
            self.after_cancel(self.toast_timer)
        if hasattr(self, 'toast_frame') and self.toast_frame.winfo_exists():
            self.toast_frame.destroy()

        # 2. 创建一个带灰色圆角背景的 Frame (直接挂在 self 上，确保在最顶层)
        self.toast_frame = ctk.CTkFrame(self, fg_color=("gray80", "gray20"), corner_radius=20)

        # 使用 place() 进行绝对定位：水平居中 (relx=0.5)，靠下 (rely=0.9)
        self.toast_frame.place(relx=0.5, rely=0.9, anchor="center")

        # 3. 在背景框里放入文字
        toast_label = ctk.CTkLabel(
            self.toast_frame, text=message, text_color=text_color,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        toast_label.pack(padx=20, pady=10)  # 给文字留出边缘空白，撑开背景

        # 4. 设定 3 秒后自动销毁这个悬浮窗
        self.toast_timer = self.after(3000, self.toast_frame.destroy)


    def set_active_tab(self, active_btn):
        """重置所有导航按钮的背景，并高亮当前选中的按钮"""
        # 1. 先把所有按钮的背景设为透明
        for btn in self.nav_tabs:
            btn.configure(fg_color="transparent")

        # 2. 给当前选中的按钮加上灰色的圆角背景 (在浅色模式下是浅灰，深色模式下是深灰)
        active_btn.configure(fg_color=("gray75", "gray25"))


    def nav_click_all_passwords(self):
        """点击 All Passwords 选项卡"""
        self.set_active_tab(self.nav_all_btn)
        self.show_password_list()


    def nav_click_add_password(self):
        """点击 Add Password 选项卡"""
        self.set_active_tab(self.nav_add_btn)
        self.show_add_password_form()


    def nav_click_settings(self):
        """点击 Settings 选项卡"""
        self.set_active_tab(self.nav_settings_btn)
        self.show_settings_page()  # 呼叫我们马上要升级的设置页面


    def show_settings_page(self):
        """显示设置页面：包含外观切换和修改主密码"""
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()

        title = ctk.CTkLabel(self.main_content_frame, text="Settings", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(anchor="w", pady=(0, 20))

        scroll_frame = ctk.CTkScrollableFrame(self.main_content_frame, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)

        # ================= 外观设置区 =================
        ctk.CTkLabel(scroll_frame, text="Appearance", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w",
                                                                                                     pady=(10, 10))

        appearance_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        appearance_frame.pack(anchor="w", fill="x", pady=(0, 20))

        ctk.CTkLabel(appearance_frame, text="Theme Mode:").pack(side="left", padx=(0, 20))

        # 切换主题的下拉菜单
        def change_appearance_mode(new_mode: str):
            ctk.set_appearance_mode(new_mode)

        theme_menu = ctk.CTkOptionMenu(
            appearance_frame, values=["System", "Dark", "Light"],
            command=change_appearance_mode
        )
        theme_menu.pack(side="left")

        # 分割线
        ctk.CTkFrame(scroll_frame, height=2, fg_color=("gray80", "gray20")).pack(fill="x", pady=10)

        # ================= 安全设置区 (修改主密码) =================
        ctk.CTkLabel(scroll_frame, text="Security: Change Master Password",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=(10, 10))

        ctk.CTkLabel(scroll_frame,
                     text="Warning: If you forget your new master password, your vault cannot be recovered.",
                     text_color="#f0ad4e", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 15))

        ctk.CTkLabel(scroll_frame, text="Current Master Password *").pack(anchor="w")
        self.entry_old_master = ctk.CTkEntry(scroll_frame, show="*", width=300)
        self.entry_old_master.pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(scroll_frame, text="New Master Password *").pack(anchor="w")
        self.entry_new_master = ctk.CTkEntry(scroll_frame, show="*", width=300)
        self.entry_new_master.pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(scroll_frame, text="Confirm New Password *").pack(anchor="w")
        self.entry_confirm_master = ctk.CTkEntry(scroll_frame, show="*", width=300)
        self.entry_confirm_master.pack(anchor="w", pady=(0, 10))

        self.change_pwd_status = ctk.CTkLabel(scroll_frame, text="", text_color="red")
        self.change_pwd_status.pack(anchor="w", pady=(5, 0))

        btn_update = ctk.CTkButton(scroll_frame, text="Update Password", command=self.handle_change_master_password)
        btn_update.pack(anchor="w", pady=(10, 0))

        # ================= 数据管理区 (Export) =================
        # 加一条灰色的分割线
        ctk.CTkFrame(scroll_frame, height=2, fg_color=("gray80", "gray20")).pack(fill="x", pady=(20, 10))

        ctk.CTkLabel(scroll_frame, text="Data Management", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w",
                                                                                                          pady=(10, 10))

        # 红色警告语，提醒用户导出的文件是明文的
        ctk.CTkLabel(
            scroll_frame,
            text="Warning: Exported CSV files contain UNENCRYPTED passwords. Keep the file safe!",
            text_color="#d9534f",  # 红色警告
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", pady=(0, 15))

        # 绿色的导出按钮
        btn_export = ctk.CTkButton(
            scroll_frame, text="📥 Export to CSV",
            fg_color="#5cb85c", hover_color="#4cae4c", text_color="white",
            command=self.handle_export_csv  # 绑定到即将写的方法
        )
        btn_export.pack(anchor="w", pady=(0, 20))


    def handle_export_csv(self):
        """将内存中的密码数据导出为明文 CSV 文件"""
        # 1. 如果金库是空的，直接提示并阻断
        if not self.vault_data:
            self.show_toast("Your vault is empty. Nothing to export.", text_color="#f0ad4e")
            return

        # 2. 弹出系统的“另存为”对话框，让用户选择保存在哪里
        filepath = filedialog.asksaveasfilename(
            title="Export Vault Data",
            defaultextension=".csv",
            initialfile="MyVault_Export.csv",  # 默认文件名
            filetypes=[("CSV File", "*.csv"), ("All Files", "*.*")]
        )

        if not filepath:
            return  # 用户点击了取消

        try:
            # 3. 打开文件，准备写入 (使用 utf-8 编码防止中文乱码)
            with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)

                # 先写入第一行的“表头” (Column Headers)
                writer.writerow(["Website/Service", "Username", "Email", "Password"])

                # 遍历内存中的每一条密码，逐行写入
                for item in self.vault_data:
                    writer.writerow([
                        item.get("site", ""),
                        item.get("username", ""),
                        item.get("email", ""),
                        item.get("password", "")
                    ])

            # 4. 导出成功，调用我们之前写的炫酷 Toast 提示！
            self.show_toast("Data exported successfully! Keep this file secure.", text_color="#5cb85c")

        except Exception as e:
            self.show_toast(f"Export failed: {e}", text_color="#d9534f")
