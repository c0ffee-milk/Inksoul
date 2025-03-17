from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import os

class AESCipher:
    def __init__(self, key=None):
        self.key = key or os.urandom(32)  # 32字节的密钥
        self.iv = os.urandom(16)  # 16字节的初始向量

    def encrypt(self, raw):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        encrypted = cipher.encrypt(pad(raw.encode(), AES.block_size))
        return base64.b64encode(self.iv + encrypted).decode()

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(enc[16:]), AES.block_size).decode()