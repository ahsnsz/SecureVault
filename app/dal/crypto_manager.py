import os
import json
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag

class CryptoManager:
    """
    Data Access Layer (DAL) Security Core.
    Responsible for handling all encryption (AES-GCM) and key derivation (Argon2id)
    """

    def __init__(self):
        # 配置 Argon2id 参数
        # 根据detail proposal ，我们需要抵抗 GPU 攻击，因此需要高内存消耗。
        self.kdf_params = {
            "algorithm": hashes.SHA256(),
            "length": 32,  # 生成 32 字节 (256-bit) 密钥，对应 AES-256
            "salt_len": 16,  # 16 字节随机 Salt
            "iterations": 2,  # 迭代次数 (Time cost)
            "memory_cost": 64 * 1024,  # 内存消耗 64MB (Memory cost) 抗 GPU 攻击
            "parallelism": 4,  # 并行度
        }


    def _derive_key(self, password: str, salt: bytes) -> bytes:
        # 密钥派生
        # 用户的密码长度不固定，也不随机。
        # AES 加密算法需要一个长度固定（32字节）且看起来完全随机的二进制串作为 Key。
        # KDF (Key Derivation Function) 就是这就负责把“弱密码”变成“强密钥”的工厂。
        # Salt (盐) 的作用：如果不加盐，两个用户如果密码都是 "123456"，生成的 Key 就一模一样。
        # 加了随机盐，就算密码一样，生成的 Key 也完全不同，防止“彩虹表”攻击。
        """
        内部方法：使用 Argon2id 将用户的主密码转换为加密密钥。
        """
        kdf = Argon2id(
            salt=salt,
            length=self.kdf_params["length"],
            iterations=self.kdf_params["iterations"],
            memory_cost=self.kdf_params["memory_cost"],
            lanes=self.kdf_params["parallelism"]
        )
        # # 将字符串密码转为 bytes 并派生
        # return kdf.derive(password.encode('utf-8'))
        # 1. 炼化出 32 字节的二进制 Key
        key = kdf.derive(password.encode('utf-8'))

        # # ==========================================
        # # 🛠️ 临时调试代码：亲眼看到造出来的Key
        # # ==========================================
        # print("\n" + "=" * 40)
        # print("🔐 [安全核心执行日志] 密钥派生成功！")
        # print(f"👉 用户输入的明文密码: {password}")
        # print(f"🧂 随机生成的 Salt (十六进制): {salt.hex()}")
        # print(f"🔑 炼化出的 AES Key (十六进制): {key.hex()}")
        # print(f"📏 Key 的精确长度: {len(key)} bytes (对应 AES-256)")
        # print("=" * 40 + "\n")
        # # ==========================================

        return key

    def encrypt_data(self, data: dict, password: str) -> bytes:
        """
        加密流程：
        1. 生成随机 Salt
        2. 派生密钥 (Key)
        3. 生成随机 Nonce
        4. AES-GCM 加密
        5. 打包返回 (Salt + Nonce + Ciphertext)
        """
        # 1. 生成唯一的随机 Salt
        salt = os.urandom(self.kdf_params["salt_len"])

        # 2. 派生密钥 (AES-256 Key) 【造钥匙：用 salt + 密码 -> 算出 AES Key】
        key = self._derive_key(password, salt)

        # 3. 初始化 AES-GCM 并生成 Nonce (IV) 【AES-GCM 需要一个“一次性数字”(Nonce)，绝不能重复】
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # GCM 标准推荐 12 字节 Nonce

        # 准备数据：将字典转为 JSON 字符串再转为 bytes
        json_data = json.dumps(data).encode('utf-8')

        # 4. 加密
        ciphertext = aesgcm.encrypt(nonce, json_data, None)

        # 5. 打包：为了方便解密，我们需要把 Salt 和 Nonce 跟密文存在一起
        # 格式: [Salt (16 bytes)] [Nonce (12 bytes)] [Ciphertext (其余)]
        return salt + nonce + ciphertext


    def decrypt_data(self, encrypted_data: bytes, password: str) -> dict:
        """
        解密流程：
        1. 提取 Salt 和 Nonce
        2. 重新派生密钥
        3. AES-GCM 解密 (自动验证完整性)
        """
        try:
            # 检查数据长度是否合法 (至少要有 Salt + Nonce)
            if len(encrypted_data) < 28:
                raise ValueError("Data corrupted")

            # 1. 提取头部信息 【拆包：按照存进去的顺序切片】
            salt = encrypted_data[:16] # 前16byte是salt
            nonce = encrypted_data[16:28] # 后面跟着的12byte是Nonce
            ciphertext = encrypted_data[28:] # 最后剩的就是密文

            # 2. 使用相同的参数和 Salt 重新派生密钥 【还原钥匙：用读出来的 Salt + 用户输入的密码 -> 算出 Key】
            key = self._derive_key(password, salt)

            # 3. 解密
            aesgcm = AESGCM(key)
            # decrypt 方法会自动验证 Tag，如果不匹配会抛出 InvalidTag 异常 【这一步用于校验身份】
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)

            # 还原为字典
            return json.loads(plaintext_bytes.decode('utf-8'))

        except InvalidTag:
            # 这是 AES-GCM 的特性，如果密码错误或文件被篡改，Tag 校验会失败 [cite: 63]
            raise ValueError("Invalid Password or Corrupted Data")
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")