import os
import json
from tkinter import filedialog
import csv
import customtkinter as ctk
import tkinter.messagebox as messagebox

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

import os
import json
from tkinter import filedialog
import customtkinter as ctk


# ==========================================
# Custom ToolTip hover widget (fixed Windows flickering version)
# ==========================================
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.id = None  # Used to store timer ID for easy cancellation

        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        """When mouse enters, don't show immediately but set a 500ms delay timer"""
        self.unschedule()
        self.id = self.widget.after(500, self.show_tooltip)

    def leave(self, event=None):
        """When mouse leaves, immediately cancel timer and destroy tooltip"""
        self.unschedule()
        self.hide_tooltip()

    def unschedule(self):
        """Cancel pending show schedule"""
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def show_tooltip(self, event=None):
        """Execute the actual logic to show tooltip"""
        self.unschedule()
        if self.tooltip_window:
            return

        # [Core fix]: Get absolute mouse position and add sufficient offset (x+15, y+15)
         # Ensure tooltip never appears directly below mouse pointer!
        x = self.widget.winfo_pointerx() + 15
        y = self.widget.winfo_pointery() + 15

        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = ctk.CTkLabel(
            self.tooltip_window,
            text=self.text,
            fg_color=("gray70", "gray30"),
            corner_radius=6,
            padx=10, pady=5,
            font=ctk.CTkFont(size=12)
        )
        label.pack()

    def hide_tooltip(self):
        """Destroy tooltip"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None




class SecureVaultApp(ctk.CTk):
    def __init__(self, vault_service):
        super().__init__()
        self.vault_service = vault_service

        # ====== Fix read-only error after packaging: Set a safe absolute path ======
        # Get the current computer user's "Documents" directory
        self.user_docs_dir = os.path.join(os.path.expanduser("~"), "Documents", "SecureVault_Data")

        # If this folder doesn't exist, create it automatically
        if not os.path.exists(self.user_docs_dir):
            os.makedirs(self.user_docs_dir)

        # Put all default database and config files into this safe folder
        default_vault = os.path.join(self.user_docs_dir, "my_vault.svdb")
        self.recent_json_path = os.path.join(self.user_docs_dir, "recent_vaults.json")
        # =======================================================

        self.vault_filepath = default_vault  # Use the new safe default path
        self.vault_data = []
        self.master_password = ""  # Initialize as empty

        self.title("SecureVault")
        self.geometry("400x500")
        self.resizable(False, False)

        # --- New: Auto-lock timer related variables ---
        self.inactivity_timer = None
        # [Note] For easy testing, this is set to 10 seconds (10000 milliseconds).
        # After successful testing, before writing the paper, please change it to 300000 (i.e., 5 minutes).
        self.timeout_ms = 300000  # 10 seconds (for testing), production version should be 300000 (5 minutes)
        self.setup_inactivity_tracker()

        self.build_login_screen()


    def get_recent_vaults(self):
        """Load the most recently used vault paths"""
        # Use the new absolute path variable
        if os.path.exists(self.recent_json_path):
            try:
                with open(self.recent_json_path, "r") as f:
                    return json.load(f)
            except:
                pass
        return []

    def add_recent_vault(self, filepath):
        """Add successfully opened vault to history, keeping at most 5 items"""
        recents = self.get_recent_vaults()
        if filepath in recents:
            recents.remove(filepath)
        recents.insert(0, filepath)
        recents = recents[:5]

        # Use the new absolute path variable
        with open(self.recent_json_path, "w") as f:
            json.dump(recents, f)


    def setup_inactivity_tracker(self):
        """Listen to global mouse and keyboard events (corresponding to Proposal Req 27)"""
        # Keyboard press, mouse click, or mouse movement will trigger reset_timer
        self.bind_all("<Any-KeyPress>", self.reset_timer)
        self.bind_all("<Any-ButtonPress>", self.reset_timer)
        self.bind_all("<Motion>", self.reset_timer)
        self.reset_timer()  # Start the initial countdown


    def reset_timer(self, event=None):
        """Each time the user performs an action, interrupt the old countdown and restart the timer"""
        if self.inactivity_timer:
            # Cancel the previously set alarm
            self.after_cancel(self.inactivity_timer)
        # Set a new alarm that will execute self.lock_vault when the time is up
        self.inactivity_timer = self.after(self.timeout_ms, self.lock_vault)


    def lock_vault(self):
        """Time's up! Lock the vault, clear memory data, return to login screen"""
        # Check: if currently at login screen (no sidebar_frame), don't need to lock again
        if not hasattr(self, 'sidebar_frame') or not self.sidebar_frame.winfo_exists():
            return

        # 1. Core security step: completely clear plaintext data and master password from memory!
        self.vault_data = []
        self.master_password = ""

        # 2. Destroy the left and right areas of the main interface to prevent data leakage
        self.sidebar_frame.destroy()
        self.main_content_frame.destroy()

        # 3. Restore the login window size
        self.geometry("400x500")

        # 4. Rebuild the login interface
        self.build_login_screen()

        # 5. Give the user a prominent orange notification
        self.status_label.configure(text="Locked due to inactivity.", text_color="#f0ad4e")


    def build_login_screen(self):
        """Build login interface, including recent vault list (restore Proposal UI/UX Mockup)"""
        # ====== Ultimate defense: clear any remaining main interface components on screen ======
        for widget in self.winfo_children():
            widget.destroy()
        # ==========================================================

        # Adjust window size to accommodate the left sidebar
        self.geometry("650x500")

        # Main container for the entire login interface
        self.login_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.login_wrapper.pack(fill="both", expand=True)

        # ==========================================
        # Left side: Recent Vaults (recent vaults)
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
                    # Click on history to directly select the file
                    command=lambda p=path: self._update_filepath_ui(p)
                )
                btn.pack(pady=5, padx=10)

        # ==========================================
        # Right side: main login form
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
        """Open system file dialog to let users select existing file (askopenfilename won't be grayed out)"""
        filepath = filedialog.askopenfilename(
            title="Open Existing Vault",
            filetypes=[("SecureVault Database", "*.svdb"), ("All Files", "*.*")]
        )
        if filepath:
            self._update_filepath_ui(filepath)


    def handle_new_file(self):
        """Open system file dialog to let users save new file (asksaveasfilename)"""
        filepath = filedialog.asksaveasfilename(
            title="Create New Vault",
            defaultextension=".svdb",
            filetypes=[("SecureVault Database", "*.svdb"), ("All Files", "*.*")]
        )
        if filepath:
            self._update_filepath_ui(filepath)


    def _update_filepath_ui(self, filepath):
        """Internal method: unified handling of interface update logic after file selection"""
        self.vault_filepath = filepath

        file_display_name = os.path.basename(self.vault_filepath)
        self.file_label.configure(text=f"Selected Vault: {file_display_name}")

        prompt_text = "Enter master password to unlock" if os.path.exists(
            self.vault_filepath) else "Create a master password for new vault"
        self.subtitle_label.configure(text=prompt_text)

        self.password_entry.delete(0, 'end')
        self.status_label.configure(text="")


    def handle_unlock(self, event=None):
        """Core logic: Handle encryption/decryption request after button click"""
        password = self.password_entry.get()

        # Save the password entered by the user to an instance attribute to let the program remember the password for later use (remembering the master password is for re-encrypting the file when "saving new data")
        self.master_password = password

        if not password:
            self.status_label.configure(text="Password cannot be empty!", text_color="red")
            return

        # Scenario 1: If vault file does not exist, create a new vault
        if not os.path.exists(self.vault_filepath):
            try:
                # Call BLL to create new vault
                self.vault_data = self.vault_service.create_new_vault(self.vault_filepath, password)
                self.status_label.configure(text="New vault created!", text_color="green")
                # [New]: After successful creation, save this file path to "recently used" history
                self.add_recent_vault(self.vault_filepath)
                # Delay 1 second before entering main interface (improve user experience)
                self.after(500, self.show_main_vault_screen)
            except Exception as e:
                self.status_label.configure(text=f"Error: {str(e)}", text_color="red")

        # Scenario 2: If vault file already exists, try to decrypt
        else:
            try:
                # Call BLL to read and decrypt
                self.vault_data = self.vault_service.load_vault(self.vault_filepath, password)
                self.status_label.configure(text="Unlocked successfully!", text_color="green")
                # [New]: After successful creation, save this file path to "recently used" history
                self.add_recent_vault(self.vault_filepath)
                # Delay 1 second before entering main interface
                self.after(500, self.show_main_vault_screen)
            except ValueError:
                # ValueError is the password error exception we throw in DAL (crypto_manager)
                self.status_label.configure(text="Invalid password! Try again.", text_color="red")
            except Exception as e:
                self.status_label.configure(text="File corrupted or unknown error.", text_color="red")


    def handle_logout(self):
        """Actively lock the vault and return to login/switch interface"""
        # Make sure we are in the main interface
        if hasattr(self, 'sidebar_frame') and self.sidebar_frame.winfo_exists():
            # 1. Core security step: completely clear plaintext data and master password from memory!
            self.vault_data = []
            self.master_password = ""

            # 2. Destroy the left and right areas of the main interface
            self.sidebar_frame.destroy()
            self.main_content_frame.destroy()

            # 3. Restore the login window size with left sidebar history
            self.geometry("650x500")

            # 4. Rebuild the login interface
            self.build_login_screen()

            # 5. Give the user a green safe logout notification
            self.status_label.configure(text="Vault locked successfully. Ready to switch.", text_color="green")


    def show_main_vault_screen(self):
        """Enter the main password vault interface (corresponding to Proposal's All Passwords interface)"""
        # ====== Ultimate fix: indiscriminate screen clearing ======
        # Traverse all components on the current main window, uproot and completely destroy them
        # This guarantees 100% that the old interface won't remain, completely preventing pack and grid conflicts!
        for widget in self.winfo_children():
            widget.destroy()
        # ======================================

        # 2. Adjust window size to fit main interface (Mockup shows this is a widescreen interface)
        self.geometry("900x600")

        # 3. Use Grid layout to divide left and right areas (column 0 is sidebar, column 1 is main content)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)  # Let the right main content area occupy all remaining space

        # ==========================================
        # Left side: Navigation Sidebar (Sidebar)
        # ==========================================
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SecureVault", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # 1. All passwords tab
        self.nav_all_btn = ctk.CTkButton(
            self.sidebar_frame, text="All Passwords", corner_radius=8,
            fg_color="transparent", text_color=("gray10", "gray90"), anchor="w",
            command=self.nav_click_all_passwords  # Bind to new highlight switching function
        )
        self.nav_all_btn.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        # 2. Add password tab
        self.nav_add_btn = ctk.CTkButton(
            self.sidebar_frame, text="+ Add Password", corner_radius=8,
            fg_color="transparent", text_color=("gray10", "gray90"), anchor="w",
            command=self.nav_click_add_password
        )
        self.nav_add_btn.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        # 3. Settings tab (replaced the original Generate and Change Password)
        self.nav_settings_btn = ctk.CTkButton(
            self.sidebar_frame, text="⚙️ Settings", corner_radius=8,
            fg_color="transparent", text_color=("gray10", "gray90"), anchor="w",
            command=self.nav_click_settings
        )
        self.nav_settings_btn.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        # Store these three buttons in a list for easy unified color switching
        self.nav_tabs = [self.nav_all_btn, self.nav_add_btn, self.nav_settings_btn]

        # Bottom red lock button remains unchanged
        self.nav_lock_btn = ctk.CTkButton(
            self.sidebar_frame, text="🔒 Lock & Switch",
            fg_color="#d9534f", hover_color="#c9302c", anchor="w",
            command=self.handle_logout
        )
        self.nav_lock_btn.grid(row=5, column=0, padx=20, pady=(50, 20), sticky="ew")
        ToolTip(self.nav_lock_btn, "Lock vault and return to login screen")

        # ==========================================
        # Right side: Main Content Area (Main Content)
        # ==========================================
        self.main_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        # When first entering the main interface, simulate clicking "All Passwords" tab by default (this way it has a highlight background)
        self.nav_click_all_passwords()

        # ====== New: Lock and Switch Vault button ======
        self.nav_lock_btn = ctk.CTkButton(
            self.sidebar_frame, text="🔒 Lock & Switch",
            fg_color="#d9534f", hover_color="#c9302c", anchor="w",  # Red warning color
            command=self.handle_logout  # Bind to active exit method
        )
        # Place in row 5 to move it down a bit
        self.nav_lock_btn.grid(row=5, column=0, padx=20, pady=(50, 20), sticky="ew")
        ToolTip(self.nav_lock_btn, "Lock vault and return to login screen")  # New

        # ==========================================
        # Right side: Main Content Area (Main Content)
        # ==========================================
        self.main_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        # When first entering the main interface, display the "All Passwords" list by default
        self.show_password_list()

    def show_password_list(self, search_query=""):
        """Display password list on the right side, supporting search and filtering (restore Proposal Req 6)"""
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()

        # --- Top: Title and search bar ---
        header_frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        title = ctk.CTkLabel(header_frame, text="All Passwords", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(side="left")

        # Search entry field
        search_entry = ctk.CTkEntry(header_frame, placeholder_text="Search site or user...", width=200)
        search_entry.pack(side="right", padx=(10, 0))
        if search_query:
            search_entry.insert(0, search_query)  # If search query exists, keep it displayed in the field

        # Internal function to trigger search
        def perform_search(*args):
            query = search_entry.get()
            self.show_password_list(search_query=query)

        # Bind Enter key to trigger search
        search_entry.bind("<Return>", perform_search)

        search_btn = ctk.CTkButton(header_frame, text="Search", width=60, command=perform_search)
        search_btn.pack(side="right")

        self.list_status_label = ctk.CTkLabel(header_frame, text="", text_color="green")
        self.list_status_label.pack(side="right", padx=20)

        # --- List area ---
        list_frame = ctk.CTkScrollableFrame(self.main_content_frame, fg_color="transparent")
        list_frame.pack(fill="both", expand=True)

        # Filter data based on search query (case-insensitive)
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

        # Render filtered cards
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

            # Red delete button
            # Find the real index of the current item in the original vault_data
            real_index = self.vault_data.index(item)
            delete_btn = ctk.CTkButton(
                card, text="Delete", width=60, fg_color="#d9534f", hover_color="#c9302c",
                command=lambda idx=real_index: self.delete_password(idx)
            )
            delete_btn.pack(side="right", padx=(0, 15))
            ToolTip(delete_btn, "Permanently delete this entry")  # New

            # --- New: Orange edit button ---
            edit_btn = ctk.CTkButton(
                card, text="Edit", width=60, fg_color="#f0ad4e", hover_color="#ec971f", text_color="black",
                # When clicked, pass this entry's index (idx) and content (itm) to the edit form
                command=lambda idx=real_index, itm=item: self.show_edit_password_form(idx, itm)
            )
            edit_btn.pack(side="right", padx=(0, 10))
            ToolTip(edit_btn, "Edit this password entry")  # New

            # Copy password button
            copy_btn = ctk.CTkButton(
                card, text="Copy", width=60,
                command=lambda pwd=item.get("password"), site=site_name: self.copy_to_clipboard(pwd, site)
            )
            copy_btn.pack(side="right", padx=(0, 10))
            ToolTip(copy_btn, "Copy password to clipboard")  # New


    def show_edit_password_form(self, index, item):
        """Display edit form and pre-fill with old password data (restore Proposal Req 5)"""
        # Clear the right content area
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()

        title = ctk.CTkLabel(self.main_content_frame, text="Edit Password", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(anchor="w", pady=(0, 20))

        form_frame = ctk.CTkScrollableFrame(self.main_content_frame, fg_color="transparent")
        form_frame.pack(fill="both", expand=True)

        # 1. Website name (pre-fill old data)
        ctk.CTkLabel(form_frame, text="Website/Service Name *").pack(anchor="w", pady=(10, 0))
        self.edit_entry_site = ctk.CTkEntry(form_frame, width=400)
        self.edit_entry_site.insert(0, item.get("site", ""))  # Insert old data
        self.edit_entry_site.pack(anchor="w", pady=(0, 10))

        # 2. Username
        ctk.CTkLabel(form_frame, text="Username").pack(anchor="w", pady=(10, 0))
        self.edit_entry_username = ctk.CTkEntry(form_frame, width=400)
        self.edit_entry_username.insert(0, item.get("username", ""))
        self.edit_entry_username.pack(anchor="w", pady=(0, 10))

        # 3. Email
        ctk.CTkLabel(form_frame, text="Email Address").pack(anchor="w", pady=(10, 0))
        self.edit_entry_email = ctk.CTkEntry(form_frame, width=400)
        self.edit_entry_email.insert(0, item.get("email", ""))
        self.edit_entry_email.pack(anchor="w", pady=(0, 10))

        # 4. Password
        ctk.CTkLabel(form_frame, text="Password *").pack(anchor="w", pady=(10, 0))
        pwd_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        pwd_frame.pack(anchor="w", fill="x")

        # Password entry field (width reduced to 240)
        self.edit_entry_password = ctk.CTkEntry(pwd_frame, show="*", width=240)
        self.edit_entry_password.insert(0, item.get("password", ""))
        self.edit_entry_password.pack(side="left", padx=(0, 5))

        # --- New: Eye icon button for Edit interface ---
        self.btn_show_edit_pwd = ctk.CTkButton(
            pwd_frame, text="👁️", width=30, fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
            command=lambda: self.toggle_password_visibility(self.edit_entry_password, self.btn_show_edit_pwd)
        )
        self.btn_show_edit_pwd.pack(side="left", padx=(0, 10))
        ToolTip(self.btn_show_edit_pwd, "Show/Hide Password")
        # -----------------------------------

        # Generate new password button
        btn_generate = ctk.CTkButton(pwd_frame, text="Generate New", width=110,
                                     command=self.handle_generate_edit_password)
        btn_generate.pack(side="left")
        ToolTip(btn_generate, "Generate a new secure password")

        self.edit_status_label = ctk.CTkLabel(form_frame, text="", text_color="red")
        self.edit_status_label.pack(anchor="w", pady=(10, 0))

        # 5. Action button area
        btn_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=(20, 0))

        # Save changes
        btn_save = ctk.CTkButton(btn_frame, text="Save Changes", command=lambda: self.handle_update_password(index))
        btn_save.pack(side="left", padx=(0, 10))

        # Cancel changes and return to list
        btn_cancel = ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", hover_color="#555555",
                                   command=self.show_password_list)
        btn_cancel.pack(side="left")

    def handle_generate_edit_password(self):
        """Generate new password in edit form"""
        new_pwd = self.vault_service.generate_random_password(length=16)
        self.edit_entry_password.delete(0, 'end')
        self.edit_entry_password.insert(0, new_pwd)
        self.edit_entry_password.configure(show="")

        # --- New: Sync update eye icon ---
        if hasattr(self, 'btn_show_edit_pwd') and self.btn_show_edit_pwd.winfo_exists():
            self.btn_show_edit_pwd.configure(text="🙈")

    def handle_update_password(self, index):
        """Collect modified data, overwrite old data, and re-encrypt and save"""
        site = self.edit_entry_site.get().strip()
        username = self.edit_entry_username.get().strip()
        email = self.edit_entry_email.get().strip()
        password = self.edit_entry_password.get()

        if not site or not password:
            self.edit_status_label.configure(text="Website and Password are required!", text_color="red")
            return

        # 1. Update data at specified index in memory
        self.vault_data[index] = {
            "site": site,
            "username": username,
            "email": email,
            "password": password
        }

        try:
            # 2. Call BLL manager to re-encrypt entire list with master password and write to disk
            self.vault_service.save_vault(self.vault_filepath, self.master_password, self.vault_data)

            # 3. After successful save, automatically jump back to password list interface
            self.show_password_list()

            # 4. Display green success message at top of list page
            self.list_status_label.configure(text=f"'{site}' updated successfully!", text_color="green")
            self.after(3000, lambda: self.list_status_label.configure(text=""))
        except Exception as e:
            self.edit_status_label.configure(text=f"Update failed: {e}", text_color="red")


    def delete_password(self, index):
        """Delete specified password and re-encrypt and save"""
        deleted_item = self.vault_data.pop(index)  # Remove from memory

        try:
            # Call BLL: overwrite old file on disk with remaining data
            self.vault_service.save_vault(self.vault_filepath, self.master_password, self.vault_data)
            # Refresh list interface
            self.show_password_list()
            self.list_status_label.configure(text=f"'{deleted_item.get('site')}' deleted!", text_color="red")
            self.after(3000, lambda: self.list_status_label.configure(text=""))
        except Exception as e:
            self.list_status_label.configure(text=f"Delete failed: {e}", text_color="red")


    def copy_to_clipboard(self, password, site_name):
        """Copy password to system clipboard and start 'Read then delete' countdown"""
        # 1. Execute copy
        self.clipboard_clear()
        self.clipboard_append(password)
        self.update()

        # 2. Update prompt text to inform user of time limit
        self.show_toast(f"Password for '{site_name}' copied! (Clears in 30s)", text_color="#5cb85c") # Green

        # 3. Read-then-delete logic: If user has already copied other passwords, cancel old countdown
        if hasattr(self, 'clipboard_timer') and self.clipboard_timer:
            self.after_cancel(self.clipboard_timer)

        # 4. Set a new 30 second (30000ms) countdown, when time's up execute clear
        self.clipboard_timer = self.after(30000, self.auto_clear_clipboard)

    def auto_clear_clipboard(self):
        """Time's up! Forcibly clear system clipboard to prevent password leakage"""
        self.clipboard_clear()
        self.clipboard_append("")  # <--- [Key fix]: Force write an empty character to completely overwrite OS clipboard
        self.update()  # Push to operating system

        self.clipboard_timer = None

        # If user is still at password list interface, give an orange security reminder
        self.show_toast("Clipboard auto-cleared for security.", text_color="#f0ad4e") # Orange


    def show_add_password_form(self):
        """Display add password form on right side, including password strength detection"""
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

        # 4. Password (contains input field, eye icon and Generate button)
        ctk.CTkLabel(form_frame, text="Password *").pack(anchor="w", pady=(10, 0))

        pwd_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        pwd_frame.pack(anchor="w", fill="x")

        # Password input field (width slightly reduced from 280 to 240)
        self.entry_password = ctk.CTkEntry(pwd_frame, placeholder_text="Enter or generate password", show="*",
                                           width=240)
        self.entry_password.pack(side="left", padx=(0, 5))

        # --- New: Eye icon button ---
        self.btn_show_pwd = ctk.CTkButton(
            pwd_frame, text="👁️", width=30, fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
            command=lambda: self.toggle_password_visibility(self.entry_password, self.btn_show_pwd)
        )
        self.btn_show_pwd.pack(side="left", padx=(0, 10))
        ToolTip(self.btn_show_pwd, "Show/Hide Password")  # Attach previously created Tooltip
        # -------------------------

        # Bind keyboard release event: check strength every time a character is entered
        self.entry_password.bind("<KeyRelease>", self.update_password_strength)

        btn_generate = ctk.CTkButton(pwd_frame, text="Generate", width=110, command=self.handle_generate_password)
        btn_generate.pack(side="left")

        # --- New: Add this line to attach hover tooltip ---
        ToolTip(btn_generate, "Click to generate a 16-character secure password")

        # --- New: Password strength display label ---
        # --- Upgraded: Password strength progress bar area ---
        self.strength_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        self.strength_frame.pack(anchor="w", pady=(10, 0), fill="x")

        # Prompt text before progress bar
        ctk.CTkLabel(self.strength_frame, text="Strength: ", font=ctk.CTkFont(size=12)).pack(side="left")

        # Core component: progress bar
        self.strength_progressbar = ctk.CTkProgressBar(self.strength_frame, width=150, height=8)
        self.strength_progressbar.pack(side="left", padx=(5, 10))
        self.strength_progressbar.set(0)  # Initial progress is 0

        # Status text after progress bar (Weak/Medium/Strong)
        self.strength_label = ctk.CTkLabel(self.strength_frame, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.strength_label.pack(side="left")

        self.add_status_label = ctk.CTkLabel(form_frame, text="", text_color="red")
        self.add_status_label.pack(anchor="w", pady=(10, 0))

        btn_save = ctk.CTkButton(form_frame, text="Save Password", command=self.handle_save_password)
        btn_save.pack(anchor="w", pady=(20, 0))


    def update_password_strength(self, event=None):
        """Real-time update password strength display and progress bar"""
        current_pwd = self.entry_password.get()
        # Receive three parameters returned by BLL: text, color, progress value
        strength_text, color, progress_value = self.vault_service.evaluate_password_strength(current_pwd)

        if strength_text:
            # Update text
            self.strength_label.configure(text=strength_text, text_color=color)
            # Update progress bar color and length
            self.strength_progressbar.configure(progress_color=color)
            self.strength_progressbar.set(progress_value)
        else:
            # If password field is cleared, restore default state
            self.strength_label.configure(text="")
            self.strength_progressbar.set(0)
            self.strength_progressbar.configure(progress_color="gray")


    def handle_generate_password(self):
        """Triggered by clicking Generate button: Call BLL to generate and display password"""
        # 1. Generate new password
        new_pwd = self.vault_service.generate_random_password(length=16)

        # 2. Clear password field and fill in new password
        self.entry_password.delete(0, 'end')
        self.entry_password.insert(0, new_pwd)

        # 3. Remove asterisk masking
        self.entry_password.configure(show="")

        # [Key fix]: Because code-inserted passwords don't trigger physical keyboard events, must manually force update once!
        self.update_password_strength()

        # --- New: Sync update eye icon ---
        if hasattr(self, 'btn_show_pwd') and self.btn_show_pwd.winfo_exists():
            self.btn_show_pwd.configure(text="🙈")


    def handle_save_password(self):
        """Triggered by clicking Save button: Collect data and encrypt and save to local"""
        site = self.entry_site.get().strip()
        username = self.entry_username.get().strip()
        email = self.entry_email.get().strip()
        password = self.entry_password.get()

        # Simple validation: website and password cannot be empty
        if not site or not password:
            self.add_status_label.configure(text="Website and Password are required!", text_color="red")
            return

        # 1. Assemble into a dictionary
        new_entry = {
            "site": site,
            "username": username,
            "email": email,
            "password": password
        }

        # 2. Append to data list in memory
        self.vault_data.append(new_entry)

        try:
            # 3. Call BLL manager to re-encrypt with master_password and write to disk
            self.vault_service.save_vault(self.vault_filepath, self.master_password, self.vault_data)
            self.add_status_label.configure(text=f"'{site}' saved successfully!", text_color="green")

            # Clear form for next entry
            self.entry_site.delete(0, 'end')
            self.entry_username.delete(0, 'end')
            self.entry_email.delete(0, 'end')
            self.entry_password.delete(0, 'end')
            self.entry_password.configure(show="*")  # Restore asterisk masking

        except Exception as e:
            self.add_status_label.configure(text=f"Save failed: {e}", text_color="red")


    def toggle_password_visibility(self, entry_widget, button_widget):
        """Generic method: toggle password field plaintext/asterisk display and change button icon"""
        if entry_widget.cget("show") == "*":
            # If currently hidden, change to display and change to "closed-eye/monkey" icon
            entry_widget.configure(show="")
            button_widget.configure(text="👁️")
        else:
            # If currently displayed, change to hidden and change to "open-eye" icon
            entry_widget.configure(show="*")
            button_widget.configure(text="🙈")


    def handle_change_master_password(self):
        """Handle logic for changing master password: verify identity -> re-encrypt -> overwrite file"""
        old_pwd = self.entry_old_master.get()
        new_pwd = self.entry_new_master.get()
        confirm_pwd = self.entry_confirm_master.get()

        # 1. Basic non-empty validation
        if not old_pwd or not new_pwd or not confirm_pwd:
            self.change_pwd_status.configure(text="All fields are required!", text_color="red")
            return

        # 2. Verify old password is correct (using self.master_password remembered during unlock)
        if old_pwd != self.master_password:
            self.change_pwd_status.configure(text="Current password is incorrect!", text_color="red")
            return

        # 3. Verify new password rules
        if new_pwd == old_pwd:
            self.change_pwd_status.configure(text="New password must be different from the old one!", text_color="red")
            return

        if new_pwd != confirm_pwd:
            self.change_pwd_status.configure(text="New passwords do not match!", text_color="red")
            return

        try:
            # 4. Call BLL manager to re-encrypt current vault_data with [new password] and overwrite save
            self.vault_service.save_vault(self.vault_filepath, new_pwd, self.vault_data)

            # 5. Very important: Update password remembered in memory to prevent using wrong old password for subsequent add/delete operations!
            self.master_password = new_pwd

            # 6. UI feedback
            self.change_pwd_status.configure(text="Master password updated successfully!", text_color="green")

            # Clear input fields
            self.entry_old_master.delete(0, 'end')
            self.entry_new_master.delete(0, 'end')
            self.entry_confirm_master.delete(0, 'end')

        except Exception as e:
            self.change_pwd_status.configure(text=f"Failed to update password: {e}", text_color="red")


    def show_toast(self, message, text_color="white"):
        """Display a floating rounded rectangle prompt box at the center bottom of window (Toast Notification)"""
        # 1. If a prompt box was previously displayed, destroy it first to prevent overlap
        if hasattr(self, 'toast_timer') and self.toast_timer is not None:
            self.after_cancel(self.toast_timer)
        if hasattr(self, 'toast_frame') and self.toast_frame.winfo_exists():
            self.toast_frame.destroy()

        # 2. Create a Frame with gray rounded background (directly attached to self to ensure topmost)
        self.toast_frame = ctk.CTkFrame(self, fg_color=("gray80", "gray20"), corner_radius=20)

        # Use place() for absolute positioning: horizontally centered (relx=0.5), at bottom (rely=0.9)
        self.toast_frame.place(relx=0.5, rely=0.9, anchor="center")

        # 3. Put text in the background frame
        toast_label = ctk.CTkLabel(
            self.toast_frame, text=message, text_color=text_color,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        toast_label.pack(padx=20, pady=10)  # Leave edge space for text, expand background

        # 4. Set to auto-destroy this floating window after 3 seconds
        self.toast_timer = self.after(3000, self.toast_frame.destroy)


    def set_active_tab(self, active_btn):
        """Reset all navigation button backgrounds and highlight currently selected button"""
        # 1. First set all button backgrounds to transparent
        for btn in self.nav_tabs:
            btn.configure(fg_color="transparent")

        # 2. Add gray rounded background to currently selected button (light gray in light mode, dark gray in dark mode)
        active_btn.configure(fg_color=("gray75", "gray25"))


    def nav_click_all_passwords(self):
        """Click 'All Passwords' tab"""
        self.set_active_tab(self.nav_all_btn)
        self.show_password_list()


    def nav_click_add_password(self):
        """Click 'Add Password' tab"""
        self.set_active_tab(self.nav_add_btn)
        self.show_add_password_form()


    def nav_click_settings(self):
        """Click 'Settings' tab"""
        self.set_active_tab(self.nav_settings_btn)
        self.show_settings_page()  # Call the settings page we're about to upgrade


    def show_settings_page(self):
        """Display settings page: containing appearance switching and changing master password"""
        for widget in self.main_content_frame.winfo_children():
            widget.destroy()

        title = ctk.CTkLabel(self.main_content_frame, text="Settings", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(anchor="w", pady=(0, 20))

        scroll_frame = ctk.CTkScrollableFrame(self.main_content_frame, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)

        # ================= Appearance Settings Area =================
        ctk.CTkLabel(scroll_frame, text="Appearance", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w",
                                                                                                     pady=(10, 10))

        appearance_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        appearance_frame.pack(anchor="w", fill="x", pady=(0, 20))

        ctk.CTkLabel(appearance_frame, text="Theme Mode:").pack(side="left", padx=(0, 20))

        # Theme switching dropdown menu
        def change_appearance_mode(new_mode: str):
            ctk.set_appearance_mode(new_mode)

        theme_menu = ctk.CTkOptionMenu(
            appearance_frame, values=["System", "Dark", "Light"],
            command=change_appearance_mode
        )
        theme_menu.pack(side="left")

        # Divider line
        ctk.CTkFrame(scroll_frame, height=2, fg_color=("gray80", "gray20")).pack(fill="x", pady=10)

        # ================= Security Settings Area (Change Master Password) =================
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

        # ====== New: Danger Zone ======
        ctk.CTkLabel(
            scroll_frame,
            text="Danger Zone",
            text_color="#d9534f",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=(20, 10))

        btn_delete_vault = ctk.CTkButton(
            scroll_frame, text="🗑️ Delete Entire Vault",
            fg_color="#d9534f", hover_color="#c9302c", text_color="white",
            command=self.handle_delete_vault  # Bind to delete method
        )
        btn_delete_vault.pack(anchor="w", pady=(0, 20))

        # ================= Data Management Area (Export) =================
        # Add a gray divider line
        ctk.CTkFrame(scroll_frame, height=2, fg_color=("gray80", "gray20")).pack(fill="x", pady=(20, 10))

        ctk.CTkLabel(scroll_frame, text="Data Management", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w",
                                                                                                          pady=(10, 10))

        # Red warning text to remind user exported files are plaintext
        ctk.CTkLabel(
            scroll_frame,
            text="Warning: Exported CSV files contain UNENCRYPTED passwords. Keep the file safe!",
            text_color="#d9534f",  # Red warning
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", pady=(0, 15))

        # Green export button
        btn_export = ctk.CTkButton(
            scroll_frame, text="📥 Export to CSV",
            fg_color="#5cb85c", hover_color="#4cae4c", text_color="white",
            command=self.handle_export_csv  # Bind to export method
        )
        btn_export.pack(anchor="w", pady=(0, 20))


    def handle_export_csv(self):
        """Export password data from memory as plaintext CSV file"""
        # 1. If vault is empty, prompt and block
        if not self.vault_data:
            self.show_toast("Your vault is empty. Nothing to export.", text_color="#f0ad4e")
            return

        # 2. Pop up system "Save As" dialog to let user choose where to save
        filepath = filedialog.asksaveasfilename(
            title="Export Vault Data",
            defaultextension=".csv",
            initialfile="MyVault_Export.csv",  # Default filename
            filetypes=[("CSV File", "*.csv"), ("All Files", "*.*")]
        )

        if not filepath:
            return  # User clicked cancel

        try:
            # 3. Open file and prepare to write (use utf-8 encoding to prevent Chinese encoding issues)
            with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)

                # First write the "header" row (Column Headers)
                writer.writerow(["Website/Service", "Username", "Email", "Password"])

                # Iterate through each password in memory and write line by line
                for item in self.vault_data:
                    writer.writerow([
                        item.get("site", ""),
                        item.get("username", ""),
                        item.get("email", ""),
                        item.get("password", "")
                    ])

            # 4. Export successful, call the cool Toast prompt we wrote earlier!
            self.show_toast("Data exported successfully! Keep this file secure.", text_color="#5cb85c")

        except Exception as e:
            self.show_toast(f"Export failed: {e}", text_color="#d9534f")

    def handle_delete_vault(self):
        """Completely delete current vault file, clean up history, and return to login screen"""
        # 1. Pop up extremely serious double confirmation warning
        confirm = messagebox.askyesno(
            "Delete Vault",
            "WARNING: This will PERMANENTLY delete your vault and all saved passwords.\n\n"
            "This action CANNOT be undone.\n\n"
            "Are you absolutely sure you want to proceed?"
        )

        if not confirm:
            return  # User clicked No, cancel operation

        try:
            # 2. Physically delete .svdb encrypted file from computer hard disk
            if os.path.exists(self.vault_filepath):
                os.remove(self.vault_filepath)

            # 3. Erase its trace from recently used history (recent_vaults.json)
            recents = self.get_recent_vaults()
            if self.vault_filepath in recents:
                recents.remove(self.vault_filepath)
                with open(self.recent_json_path, "w") as f:
                    json.dump(recents, f)

            # 4. Force user exit and return to login screen
            self.handle_logout()

        except Exception as e:
            self.show_toast(f"Failed to delete vault: {e}", text_color="#d9534f")