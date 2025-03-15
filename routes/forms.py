#forms.py : 主要用来验证前端提交的数据是否合法
# 标准库导入
import wtforms

# 第三方库导入
from flask_wtf import FlaskForm  # 使用 FlaskForm 而不是 wtforms.Form
from wtforms import StringField, SubmitField
from wtforms.validators import Email, Length, EqualTo, InputRequired

# 本地模块导入
from models import UserModel, EmailCaptchaModel
from exts import db

class RegisterForm(FlaskForm):  # 继承 FlaskForm
    email = StringField(validators=[Email(message="邮箱格式错误！")])
    captcha = StringField(validators=[Length(min=4, max=4, message="验证码格式错误！")])
    username = StringField(validators=[Length(min=3, max=20, message="用户名格式错误！")])
    password = StringField(validators=[Length(min=6, max=20, message="密码格式错误！")])
    password_confirm = StringField(validators=[EqualTo("password", message="两次密码不一致")])
    submit = SubmitField()

    # 自定义验证：邮箱是否已经存在
    # field：当前输入的字段 captcha self:表单对象
    def validate_email(self, field):
        email = field.data
        user = UserModel.query.filter_by(email=email).first()
        if user:
            raise wtforms.ValidationError(message="该邮箱已经被注册！")

    # 自定义验证：验证码是否正确
    def validate_captcha(self, field):
        captcha = field.data
        email = self.email.data
        captcha_model = EmailCaptchaModel.query.filter_by(email=email, captcha=captcha).first()
        if not captcha_model:
            raise wtforms.ValidationError(message="邮箱或验证码错误！")
        #后续可以优化为定期清理，现在会影响数据库的性能
        else:
            db.session.delete(captcha_model)
            db.session.commit()


class LoginForm(FlaskForm):  # 继承 FlaskForm
    email = StringField(validators=[Email(message="邮箱格式错误！")])
    password = StringField(validators=[Length(min=6, max=20, message="密码格式错误！")])
    submit = SubmitField()


class ChangeForm(FlaskForm):  # 继承 FlaskForm
    email = StringField(validators=[Email(message="邮箱格式错误！")])
    captcha = StringField(validators=[Length(min=4, max=4, message="验证码格式错误！")])
    password = StringField(validators=[Length(min=6, max=20, message="密码格式错误！")])
    password_confirm = StringField(validators=[EqualTo("password", message="两次密码不一致")])
    submit = SubmitField()

    def validate_email(self, field):
        email = field.data
        user = UserModel.query.filter_by(email=email).first()
        if not user:
            raise wtforms.ValidationError(message="该邮箱还未注册")

    def validate_captcha(self, field):
        captcha = field.data
        email = self.email.data
        captcha_model = EmailCaptchaModel.query.filter_by(email=email, captcha=captcha).first()
        if not captcha_model:
            raise wtforms.ValidationError(message="邮箱或验证码错误！")


class DiaryForm(FlaskForm):  # 继承 FlaskForm
    title = StringField(validators=[
        InputRequired(message="标题不能为空！"),
        Length(max=100, message="标题长度不能超过100个字符！")
    ])
    content = StringField(validators=[
        InputRequired(message="内容不能为空！")
    ])
    submit = SubmitField("提交")

    # 自定义验证：标题和内容不能为空
    def validate_title(self, field):
        if not field.data.strip():
            raise wtforms.ValidationError(message="标题不能为空！")

    def validate_content(self, field):
        if not field.data.strip():
            raise wtforms.ValidationError(message="内容不能为空！")

