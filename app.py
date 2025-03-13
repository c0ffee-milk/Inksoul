#入口文件
from flask import Flask,g,session
from flask_moment import Moment
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from exts import db, mail
from models import UserModel
from sqlalchemy import text
from flask_migrate import Migrate
# 导入蓝图
from routes.auth import bp as auth_bp
from routes.diary import bp as diary_bp
from routes.index import bp as index_bp
#实例化Flask应用并配置应用参数
app = Flask(__name__)
app.config.from_pyfile('setting.py')
moment = Moment(app)


# 注册蓝图到Flask应用，设置URL前缀
app.register_blueprint(auth_bp)
app.register_blueprint(diary_bp)
app.register_blueprint(index_bp)

#初始化db，先创建，再绑定，避免循环引用
db.init_app(app)
mail.init_app(app)

#创建Migrate对象
migrate = Migrate(app, db)
#flask db init  #初始化迁移环境
#flask db migrate  #生成迁移脚本
#flask db upgrade  #执行迁移
#flask db downgrade  #回滚迁移




#检测数据库是否连接
with app.app_context():
    with db.engine.connect() as conn:
        rs = conn.execute(text('select 1'))#运行后终端输出1
        print(rs.fetchone())



@app.before_request
def my_before_request():
    user_id = session.get('user_id')
    if user_id:
        user = UserModel.query.get(user_id)
        setattr(g, "user", user)
    else:
        setattr(g, "user", None)


@app.context_processor
def my_context_processor():
    return {'user': g.user}


# 主程序入口，判断当前模块是否是主模块，如果是则启动Flask应用
if __name__ == '__main__':
    app.run(debug=True)
