# 入口文件
from flask import Flask, g, session
from flask_login import LoginManager
from flask_mail import Message
from flask_migrate import Migrate
from flask_moment import Moment
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import text

# 导入自定义模块
from exts import db, mail
from models import UserModel
from routes.auth import bp as auth_bp
from routes.diary import bp as diary_bp
from routes.index import bp as index_bp

from dotenv import load_dotenv

load_dotenv()

# 实例化 Flask 应用并配置应用参数
import json


app = Flask(__name__)

@app.template_filter('fromjson')
def fromjson_filter(value):
    """将 JSON 字符串转换为 Python 对象"""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value
csrf = CSRFProtect(app)
app.config.from_pyfile('setting.py')
moment = Moment(app)

# 初始化 LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# 加载用户的回调函数
@login_manager.user_loader
def load_user(user_id):
    from models import UserModel
    return UserModel.query.get(int(user_id))

# 注册蓝图到 Flask 应用，设置 URL 前缀
app.register_blueprint(auth_bp)
app.register_blueprint(diary_bp)
app.register_blueprint(index_bp)

# 初始化 db，先创建，再绑定，避免循环引用
db.init_app(app)
mail.init_app(app)

# 创建 Migrate 对象
migrate = Migrate(app, db)

# 检测数据库是否连接（开发调试）
# with app.app_context():
#     with db.engine.connect() as conn:
#         rs = conn.execute(text('select 1'))  # 运行后终端输出 1
#         print(rs.fetchone())

# 请求前处理
@app.before_request
def my_before_request():
    user_id = session.get('user_id')
    if user_id:
        user = UserModel.query.get(user_id)
        setattr(g, "user", user)
    else:
        setattr(g, "user", None)

# 上下文处理器
@app.context_processor
def my_context_processor():
    return {'user': g.user}

# 获取网页logo
@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('image.svg')


# 主程序入口
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
