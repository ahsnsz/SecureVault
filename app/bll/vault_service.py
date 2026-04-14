import os
import secrets
import string
from app.dal.crypto_manager import CryptoManager

# Business Logic Layer BLL层
# Responsible for coordinating between the GUI and DAL layers
# handling file I/O and password generation
class VaultService:
    def __init__(self):
        #实例化数据访问层DAL（也就是crypto_manager），并将其作为属性保存到BLL中
        #这样BLL就可以随时调用底层的加密和解密功能了
        self.crypto_manager = CryptoManager()

    #生成随机密码
    def generate_random_password(self, length=16, use_upper=True, use_digits=True, use_symbols=True) -> str:

        #密码字符集：大小写字母、数字和特殊符号
        chars = string.ascii_lowercase  # 默认包含小写字母 (a-z)
        if use_upper:
            chars += string.ascii_uppercase  # 加入大写字母 (A-Z)
        if use_digits:
            chars += string.digits  # 加入数字 (0-9)
        if use_symbols:
            chars += "!@#$%^&*"  # 加入特殊符号

        #使用 secrets 模块生成安全随机密码
        #secrets.choice(chars) 会从 chars 中随机选择一个字符，循环 length 次生成指定长度的密码
        #这里不使用 random 模块，因为 random 生成的是伪随机数，而 secrets 模块则使用系统级的随机数生成器，适合生成密码和密钥
        return ''.join(secrets.choice(chars) for _ in range(length))

    def evaluate_password_strength(self, password: str) -> tuple[str, str, float]:
        """
        评估密码强度
        返回一个元组: (强度文本, 颜色十六进制, 进度条数值0.0~1.0)
        """
        if not password:
            return "", "transparent", 0.0

        score = 0
        # 1. 长度加分
        if len(password) >= 8: score += 1
        if len(password) >= 12: score += 1

        # 2. 复杂性加分
        if any(c.isupper() for c in password): score += 1
        if any(c.islower() for c in password): score += 1
        if any(c.isdigit() for c in password): score += 1
        if any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password): score += 1

        # 3. 评级与进度分配
        if score < 3:
            return "Weak", "#d9534f", 0.33  # 红色, 进度 33%
        elif score < 5:
            return "Medium", "#f0ad4e", 0.66  # 橙色, 进度 66%
        else:
            return "Strong", "#5cb85c", 1.0  # 绿色, 进度 100%

    #实现保存密码库的功能
    def save_vault(self, filepath: str, master_password: str, data: list):
        # 将用户的明文密码列表，加密并写入本地文件。
        # 1. 呼叫 DAL：把明文数据 (data) 和主密码 (master_password) 交给加密核心
        # 返回的 encrypted_data 是毫无规律的二进制乱码 (bytes)
        encrypted_data = self.crypto_manager.encrypt_data(data, master_password)

        # 2. 写入本地文件
        # ‘wb’就是写入二进制)。
        # 因为经过 AES 加密后的数据已经不是普通的文本了，必须用二进制模式保存。
        with open(filepath, 'wb') as f:
            f.write(encrypted_data)

    #实现加载密码库的功能
    def load_vault(self, filepath: str, master_password: str) -> list:
        """
        从本地读取加密文件，并解密还原为明文列表。
        """
        # 1. 检查文件存不存在
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"找不到密码库文件: {filepath}")

        # 2. 读取二进制文件
        # 'rb' 的意思是 Read Binary (读取二进制)
        with open(filepath, 'rb') as f:
            encrypted_data = f.read()

        # 3. 呼叫 DAL：将读到的乱码和用户输入的主密码交还给核心去解密
        # 如果密码不对，或者文件被篡改，这里会自动报错 (我们在 DAL 里写好的 ValueError)
        decrypted_data = self.crypto_manager.decrypt_data(encrypted_data, master_password)

        # 4. 返回明文数据给 GUI 去显示
        return decrypted_data

    #实现创建新的空密码库的文件
    def create_new_vault(self, filepath: str, master_password: str) -> list:
        """创建一个新的空密码库文件"""
        empty_data = []  # 初始为空列表
        self.save_vault(filepath, master_password, empty_data)
        return empty_data