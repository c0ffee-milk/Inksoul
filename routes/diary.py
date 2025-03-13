from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_pagination import Pagination
from models import DiaryModel, UserModel
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
    # 更新用户的 diary_count
            user = UserModel.query.get(current_user.id)
            user.diary_count += 1
            db.session.commit()
            flash('日记添加成功', 'success')
            return redirect(url_for('index'))
    return render_template('index.html')

@bp.route('/edit/<int:diary_id>', methods=['GET', 'POST'])
@login_required
def edit(diary_id):
    diary = DiaryModel.query.get(diary_id)
    if diary.author_id == current_user.id:
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            if not title or not content:
                return redirect(url_for('diary.edit', diary_id=diary_id))
            else:
                diary.title = title
                diary.content = content
                db.session.commit()
                return redirect(url_for('index'))
        return render_template('edit.html', diary=diary)
    else:
        return redirect(url_for('index'))

@bp.route('/delete/<int:diary_id>', methods=['GET', 'POST'])
@login_required
def delete(diary_id):
    diary = DiaryModel.query.get(diary_id)
    if diary.author_id == current_user.id:
        db.session.delete(diary)
        db.session.commit()
        # 更新用户的 diary_count
        user = UserModel.query.get(current_user.id)
        user.diary_count -= 1
        db.session.commit()
        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))