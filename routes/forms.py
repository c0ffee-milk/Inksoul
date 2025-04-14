#forms.py : 主要用来验证前端提交的数据是否合法
# 标准库导入
import wtforms

# 第三方库导入
from wtforms import BooleanField 
from flask_wtf import FlaskForm  # 使用 FlaskForm 而不是 wtforms.Form
from wtforms import StringField, SubmitField
from wtforms.validators import Email, Length, EqualTo, InputRequired

# 本地模块导入
from models import UserModel, EmailCaptchaModel
from exts import db

class RegisterForm(FlaskForm):  # 注册表单类
    # 邮箱字段，使用Email验证器检查格式
    email = StringField(validators=[Email(message="邮箱格式错误！")])
    # 验证码字段，限制长度为4位
    captcha = StringField(validators=[Length(min=4, max=4, message="验证码格式错误！")])
    # 用户名字段，长度限制3-20个字符
    username = StringField(validators=[Length(min=3, max=20, message="用户名格式错误！")])
    # 密码字段，长度限制6-20个字符
    password = StringField(validators=[Length(min=6, max=20, message="密码格式错误！")])
    # 确认密码字段，需要与password字段一致
    password_confirm = StringField(validators=[EqualTo("password", message="两次密码不一致")])
    # 提交按钮
    submit = SubmitField()

    def validate_email(self, field):
        """验证邮箱是否已被注册"""
        email = field.data
        user = UserModel.query.filter_by(email=email).first()
        if user:
            raise wtforms.ValidationError(message="该邮箱已经被注册！")

    def validate_captcha(self, field):
        """验证验证码是否正确且未过期"""
        captcha = field.data
        email = self.email.data
        captcha_model = EmailCaptchaModel.query.filter_by(email=email, captcha=captcha).first()
        if not captcha_model:
            raise wtforms.ValidationError(message="邮箱或验证码错误！")
        else:
            # 验证通过后删除验证码记录，防止重复使用
            db.session.delete(captcha_model)
            db.session.commit()

class LoginForm(FlaskForm):  # 登录表单类
    # 记住我复选框
    remember_me = BooleanField('记住我')
    # 邮箱字段
    email = StringField(validators=[Email(message="邮箱格式错误！")])
    # 密码字段
    password = StringField(validators=[Length(min=6, max=20, message="密码格式错误！")])
    # 提交按钮
    submit = SubmitField()

class ChangeForm(FlaskForm):  # 修改密码表单类
    # 邮箱字段
    email = StringField(validators=[Email(message="邮箱格式错误！")])
    # 验证码字段
    captcha = StringField(validators=[Length(min=4, max=4, message="验证码格式错误！")])
    # 新密码字段
    password = StringField(validators=[Length(min=6, max=20, message="密码格式错误！")])
    # 确认新密码字段
    password_confirm = StringField(validators=[EqualTo("password", message="两次密码不一致")])
    # 提交按钮
    submit = SubmitField()

    def validate_email(self, field):
        """验证邮箱是否已注册"""
        email = field.data
        user = UserModel.query.filter_by(email=email).first()
        if not user:
            raise wtforms.ValidationError(message="该邮箱还未注册")

    def validate_captcha(self, field):
        """验证验证码是否正确"""
        captcha = field.data
        email = self.email.data
        captcha_model = EmailCaptchaModel.query.filter_by(email=email, captcha=captcha).first()
        if not captcha_model:
            raise wtforms.ValidationError(message="邮箱或验证码错误！")

class DiaryForm(FlaskForm):  # 日记表单类
    # 日记标题字段，必填且最大长度100字符
    title = StringField(validators=[
        InputRequired(message="标题不能为空！"),
        Length(max=100, message="标题长度不能超过100个字符！")
    ])
    # 日记内容字段，必填
    content = StringField(validators=[
        InputRequired(message="内容不能为空！")
    ])
    # 提交按钮
    submit = SubmitField("提交")

    def validate_title(self, field):
        """验证标题不能仅为空白字符"""
        if not field.data.strip():
            raise wtforms.ValidationError(message="标题不能为空！")

    def validate_content(self, field):
        """验证内容不能仅为空白字符"""
        if not field.data.strip():
            raise wtforms.ValidationError(message="内容不能为空！")

class TimeForm(FlaskForm):  # 时间范围表单类
    # 开始时间字段，必填
    start_time = StringField(validators=[InputRequired(message="开始时间不能为空！")])
    # 结束时间字段，必填
    end_time = StringField(validators=[InputRequired(message="结束时间不能为空！")])
    # 提交按钮
    submit = SubmitField("提交")
    



