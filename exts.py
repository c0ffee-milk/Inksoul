#这个文件用来避免出现循环导入问题

from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

#不能传app，避免循环引用
db = SQLAlchemy()
mail = Mail()