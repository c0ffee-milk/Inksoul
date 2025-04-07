from email.policy import default

from flask_login import UserMixin
from sqlalchemy.engine import create
from exts import db
from datetime import datetime
from sqlalchemy import JSON

# 用户模型
class UserModel(db.Model,UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(1000), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    join_time = db.Column(db.DateTime, default=datetime.now)
    def ping(self):
        self.last_login = datetime.utcnow()
        db.session.add(self)
    
    diaries = db.relationship('DiaryModel', backref='author', lazy='dynamic')

    # Flask-Login 需要的方法
    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

# 邮箱验证码模型
class EmailCaptchaModel(db.Model):
    __tablename__ = "email_captcha"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), nullable=False)
    captcha = db.Column(db.String(100), nullable=False)


# 日记模型
class DiaryModel(db.Model):
    __tablename__ = "diary"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now)
    analyze = db.Column(JSON)
    emotion_type = db.Column(db.String(100), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    if_analyze = db.Column(db.Boolean, default=False)  # 新增字段，用于标记是否已分析

    # 添加日期访问器（兼容原热力图逻辑）
    @property
    def date(self):
        return self.create_time.date()

class WeeklyModel(db.Model):
    __tablename__ = "weekly_report"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    create_time = db.Column(db.DateTime, default=datetime.now)
    content = db.Column(JSON)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    diary_nums = db.Column(db.Integer)

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    

