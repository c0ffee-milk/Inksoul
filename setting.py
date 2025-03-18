# Flask应用密钥
SECRET_KEY = "sdafewafewwqfgdsf"

# 数据库配置
HOSTNAME = "127.0.0.1"
PORT = 3306
USERNAME = "root"
PASSWORD = "14618983"
DATABASE = "database_inksoul"
DB_URI = 'mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8mb4'.format(USERNAME,PASSWORD,HOSTNAME,PORT,DATABASE)
SQLALCHEMY_DATABASE_URI = DB_URI

# 邮件服务器配置
MAIL_SERVER = "smtp.qq.com"
MAIL_PORT = 465
MAIL_USERNAME = "2838651487@qq.com"
MAIL_PASSWORD = "gzmjslyhaintdheg"
MAIL_DEFAULT_SENDER = "2838651487@qq.com"
MAIL_USE_SSL = True

# 分页配置
PER_PAGE_COUNT = 10

# 设置记住我功能的cookie有效期，单位为秒（默认365天）
REMEMBER_COOKIE_DURATION = 30 * 24 * 60 * 60  # 30天