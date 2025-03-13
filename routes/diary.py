from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_pagination import Pagination
from models import DiaryModel
from flask_login import current_user, login_required
from exts import db
bp = Blueprint('diary', __name__, url_prefix='/diary')

@bp.route('/')
def index():
    if current_user.is_authenticated:
        # 获取当前用户的所有日记，按创建时间倒序排列
        diaries = DiaryModel.query.filter_by(author_id=current_user.id).order_by(DiaryModel.create_time.desc()).all()
    else:
        return redirect(url_for('auth.login'))
    return render_template('index.html', diaries=diaries)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        if not title or not content:
            flash('日记和标题不能为空')
            return redirect(url_for('diary.add'))
        else:
            # 创建日记并保存到数据库
            diary = DiaryModel(title=title, content=content, user_id=current_user.id)
            db.session.add(diary)
            db.session.commit()
            flash('日记添加成功', 'success')
            return redirect(url_for('index'))
    return render_template('index.html')