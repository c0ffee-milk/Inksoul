# auth.py
# 标准库导入
import random
import string
import os

# 第三方库导入
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, abort
from flask_wtf import form
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.widgets import PasswordInput
from flask_login import current_user, login_user, logout_user
from datetime import datetime
from dotenv import load_dotenv

# 本地模块导入
from exts import mail, db
from models import EmailCaptchaModel, UserModel
from .forms import RegisterForm, LoginForm, ChangeForm
from models import DiaryModel
from utils.crypto import AESCipher
from LLM.llm import EmotionAnalyzer 
from data.auto_create_diaries import AUTO_CREATE_DIARIES

# 加载.env文件
load_dotenv()

# 初始化加密器
cipher = AESCipher(key=os.getenv("AES_KEY").encode())

# 创建蓝图
bp = Blueprint("auth", __name__, url_prefix="/auth")

# 登录路由
@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('diary.mine'))
    form = LoginForm(request.form)
    if request.method == "GET":
        return render_template("login.html", form=form)
    else:
        if form.validate_on_submit():
            email = form.email.data
            password = form.password.data
            if password is None:
                flash("密码不能为空")
                return redirect(url_for("auth.login"))
            user = UserModel.query.filter_by(email=email).first()
            if not user:
                flash("用户未找到")
                return redirect(url_for("auth.login"))
            if check_password_hash(user.password, password):
                # 添加 remember 参数
                remember = form.remember_me.data if hasattr(form, 'remember_me') else False
                login_user(user, remember=remember)
                flash("成功登录")
                return redirect(url_for("diary.mine"))
            else:
                flash("密码错误")
                return redirect(url_for("auth.login"))
        else:
            flash("表单错误：" + str(form.errors))
            return redirect(url_for("auth.login"))

# 注册新用户的路由(注册时自动添加日记)
@bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password.data
        
        hashed_password = generate_password_hash(password)
        user = UserModel(email=email, username=username, password=hashed_password)
        
        try:
            # 开始事务
            db.session.add(user)
            db.session.flush()  # 获取user.id但不提交事务
            
            # 创建分析器实例
            analyzer = EmotionAnalyzer(f"U{user.id}")
            
            # 添加自动创建的日记
            for diary_data in AUTO_CREATE_DIARIES:
                # 先创建日记对象获取统一时间，确保向量数据库和关系数据库的时间一致
                diary = DiaryModel(
                    title=diary_data["title"],
                    content='',  # 临时占位
                    author_id=user.id,
                    create_time=datetime.strptime(diary_data["time"], "%Y-%m-%d")
                )
                db.session.add(diary)
                db.session.flush()  # 生成create_time但不提交事务
                
                # 记录日记到向量数据库(使用与SQL数据库相同的时间戳)
                create_time_str = diary.create_time.strftime('%Y-%m-%d %H:%M:%S')
                content_to_log = diary_data["content"]
                analyzer.log_diary(text=f"[{create_time_str}]\n{content_to_log}", timestamp=int(datetime.strptime(diary_data["time"], "%Y-%m-%d").timestamp()))
                
                # 加密并更新日记内容
                diary.content = cipher.encrypt(diary_data["content"])

            #提交日记到关系数据库
            db.session.commit()
            flash('注册成功，请登录', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'注册失败: {str(e)}', 'error')
    return render_template('register.html', form=form)

# 获取邮箱验证码的路由
@bp.route("/captcha/email", methods=["GET"])
def get_email_captcha():
    email = request.args.get('email')
    if not email:
        return jsonify({"code": 400, "message": "请提供邮箱地址"})
    
    # 检查邮箱是否已注册
    if UserModel.query.filter_by(email=email).first():
        return jsonify({"code": 400, "message": "该邮箱已注册"})
        
    captcha = ''.join(random.choices(string.digits, k=4))
    message = Message(subject="心灵日记验证码", recipients=[email], body=f"您的验证码是: {captcha}")
    try:
        mail.send(message)
        captcha_model = EmailCaptchaModel(email=email, captcha=captcha)
        db.session.add(captcha_model)
        db.session.commit()
        return jsonify({"code": 200, "message": "验证码发送成功"})
    except Exception as e:
        return jsonify({"code": 500, "message": "验证码发送失败"})

# 退出登录的路由
@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('index.index_page'))

# 修改密码的路由
@bp.route("/change_password", methods=["GET", "POST"])
def change_password():
    form = ChangeForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = UserModel.query.filter_by(email=email).first()
        if user:
            user.password = generate_password_hash(password)
            db.session.commit()
            flash('密码修改成功，请使用新密码登录', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('邮箱未注册', 'error')
    return render_template('change_password.html', form=form)