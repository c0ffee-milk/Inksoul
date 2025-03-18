#auth
# 标准库导入
import random
import string

# 第三方库导入
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, abort
from flask_wtf import form
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.widgets import PasswordInput
from flask_login import current_user,login_user,logout_user

# 本地模块导入
from exts import mail, db
from models import EmailCaptchaModel, UserModel
from .forms import RegisterForm, LoginForm, ChangeForm



bp = Blueprint("auth", __name__,url_prefix="/auth")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('diary.mine'))
    form = LoginForm(request.form)
    if request.method == "GET":
        return render_template("login.html",form = form)
    else:
        # 检查表单格式
        if form.validate_on_submit():
            email = form.email.data
            password = form.password.data
            if password is None:
                    flash("密码不能为空")
                    return redirect(url_for("auth.login"))
            user = UserModel.query.filter_by(email=email).first()
            # 检查是否存在该用户
            if not user:
                flash("用户未找到")
                return redirect(url_for("auth.login"))
            # 检查密码
            if check_password_hash(user.password, password):
                login_user(user)
                flash("成功登录")
                return redirect(url_for("diary.mine"))
            else:
                flash("密码错误")
                return redirect(url_for("auth.login"))
        else:
            flash("表单错误：" + str(form.errors))
            return redirect(url_for("auth.login"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "GET":
        return render_template("register.html",form=form)
    else:
        # 验证用户提交的邮箱和验证码是否对应且正确
        if form.validate_on_submit():
            email = form.email.data
            username = form.username.data
            password = form.password.data
            if not email or not username or not password:
                flash("邮箱、用户名和密码不能为空")
                return redirect(url_for("auth.register"))
            # 验证成功，创建用户
            user = UserModel(username=username, email=email, password=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()

            flash("注册成功，请登录")
            return redirect(url_for("auth.login"))
        # 注册失败
        else:
            print(form.errors)
            return redirect(url_for("auth.register"))


@bp.route("/captcha/email", methods=["GET"])
def get_email_captcha():
    try:
        # 获取注册用户邮箱
        email = request.args.get("email")
        if not email:
            return jsonify({"code": 400, "message": "邮箱不能为空", "data": None})
        # 生成验证码
        source = string.digits * 4
        captcha = random.sample(source, 4)
        captcha = "".join(captcha)
        # 发送验证码给注册用户
        message = Message(
            subject="您的InkSoul注册码",
            recipients=[email],
            html=f"""
            <html>
                <body>
                    <h2 style="color: #4CAF50;">欢迎使用InkSoul</h2>
                    <p>您的验证码是：<strong style="font-size: 18px; color: #2196F3;">{captcha}</strong></p>
                    <p>请妥善保管，该验证码将在15分钟后失效。</p>
                    <hr style="border: 1px solid #ddd;">
                    <p style="color: #888; font-size: 12px;">此为系统自动发送邮件，请勿直接回复。</p>
                </body>
            </html>
            """
        )
        mail.send(message)
        # 将验证码存入数据库（后续再进行优化，缺陷：存储与提取速度慢）使用memcached/redis
        email_captcha = EmailCaptchaModel(email=email, captcha=captcha)
        db.session.add(email_captcha)
        db.session.commit()
        #RESTful API规范，返回JSON响应
        return jsonify({"code": 200, "message": "验证码已发送", "data": None})
    except Exception as e:
        print(f"发送验证码时出现错误: {e}")
        return jsonify({"code": 500, "message": "发送验证码时出现错误", "data": None})
        


@bp.route("/logout")
def logout():
    logout_user()
    return redirect("/")


@bp.route("/change_password", methods=["GET", "POST"])
def change_password():
    if request.method == "GET":
        return render_template("change_password.html")
    else:
        form = ChangeForm(request.form)
        if form.validate():
            user = UserModel.query.filter_by(email=form.email.data).first()
            password = form.password.data
            if not password:
                flash("密码不能为空")
                return redirect(url_for("auth.change_password"))
            user.password = generate_password_hash(password)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for("auth.login"))
        else:
            print(form.errors)
            return redirect(url_for("auth.change_password"))
