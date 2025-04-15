# 导入加密相关库
from Cryptodome.Cipher import AES  # AES加密算法
from Cryptodome.Util.Padding import pad, unpad  # 填充处理
import base64  # Base64编码解码
import os  # 操作系统相关功能

class AESCipher:
    """AES加密解密工具类(CBC模式)"""
    
    def __init__(self, key=None):
        """初始化加密器
        Args:
            key: 可选参数，32字节的AES密钥，不传则随机生成
        """
        self.key = key or os.urandom(32)  # 32字节(256位)的密钥
        self.iv = os.urandom(16)  # 16字节的初始向量(IV)

    def encrypt(self, raw):
        """加密原始字符串
        Args:
            raw: 要加密的原始字符串
        Returns:
            Base64编码的加密结果(包含IV)
        """
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)  # 创建AES-CBC加密器
        encrypted = cipher.encrypt(pad(raw.encode(), AES.block_size))  # 填充后加密
        return base64.b64encode(self.iv + encrypted).decode()  # 返回IV+密文的Base64

    def decrypt(self, enc):
        """解密加密字符串
        Args:
            enc: Base64编码的加密字符串
        Returns:
            解密后的原始字符串
        """
        enc = base64.b64decode(enc)  # Base64解码
        iv = enc[:16]  # 提取前16字节作为IV
        cipher = AES.new(self.key, AES.MODE_CBC, iv)  # 创建AES-CBC解密器
        return unpad(cipher.decrypt(enc[16:]), AES.block_size).decode()  # 解密后去除填充