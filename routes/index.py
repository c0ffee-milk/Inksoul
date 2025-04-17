# 导入Flask相关模块和登录状态管理
from flask import render_template, Blueprint, redirect, url_for
from flask_login import current_user

# 创建蓝图实例，设置URL前缀为根路径
bp = Blueprint('index', __name__, url_prefix="/")

# 定义根路由('/')的处理函数
@bp.route('/')
def index_page():
    # 检查用户是否已认证(登录)
    if current_user.is_authenticated:
        # 已登录用户重定向到日记列表页
        return redirect(url_for('diary.mine'))
    # 未登录用户显示介绍页
    return render_template('intro.html')