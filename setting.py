import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Flask应用密钥
SECRET_KEY = os.getenv('SECRET_KEY', 'sdafewafewwqfgdsf')

# 数据库配置
HOSTNAME = os.getenv('DB_HOST', '127.0.0.1')  # 修改为127.0.0.1更安全
PORT = int(os.getenv('DB_PORT', '3306'))
USERNAME = os.getenv('DB_USER', 'root')
PASSWORD = os.getenv('DB_PASSWORD', '14618983')
DATABASE = os.getenv('DB_NAME', 'database_inksoul')
DB_URI = f'mysql+pymysql://{USERNAME}:{PASSWORD}@{HOSTNAME}:{PORT}/{DATABASE}?charset=utf8mb4'
SQLALCHEMY_DATABASE_URI = DB_URI

# 邮件服务器配置
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.qq.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', '465'))
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'True').lower() == 'true'

# 设置记住我功能的cookie有效期
REMEMBER_COOKIE_DURATION = int(os.getenv('REMEMBER_COOKIE_DURATION', '2592000'))  # 30天