from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_pagination import Pagination
from models import DiaryModel, UserModel, WeeklyModel
from flask_login import current_user, login_required
from exts import db
from LLM.llm import EmotionAnalyzer  # 新增导入
from datetime import datetime  # 新增导入
from utils.crypto import AESCipher
import json
bp = Blueprint('diary', __name__, url_prefix='/diary')

# 在应用启动时初始化加密器
cipher = AESCipher(key=b'your-32-byte-secret-key')  # 使用固定密钥或从配置中读取

@bp.route('/mine')
@login_required
def mine():
    # 获取当前用户的所有日记，按创建时间倒序排列
    diaries = DiaryModel.query.filter_by(author_id=current_user.id).order_by(DiaryModel.create_time.desc()).all()
    # 解密日记内容
    decrypted_diaries = []
    for diary in diaries:
        decrypted_content = cipher.decrypt(diary.content)
        decrypted_analysis = json.loads(cipher.decrypt(diary.analyze)) if diary.analyze else None
        decrypted_diaries.append({
            'id': diary.id,
            'title': diary.title,
            'content': decrypted_content,
            'analyze': decrypted_analysis,
            'create_time': diary.create_time
        })
    return render_template('index.html', diaries=decrypted_diaries)
    

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
            encrypted_content = cipher.encrypt(content)
            diary = DiaryModel(title=title, content=encrypted_content, author_id=current_user.id) 
            db.session.add(diary)
            db.session.commit()
            # 调用情感分析
            analyzer = EmotionAnalyzer(current_user.id)
            # 去除换行符
            cleaned_content = content.replace('\n', ' ').replace('\r', '')
            analysis_result = analyzer.analyze(
                mode="daily",
                diary=cleaned_content,  # 使用处理后的内容
                date=datetime.now()
            )
            encrypted_analysis = cipher.encrypt(json.dumps(analysis_result, ensure_ascii=False))
            diary.analyze = encrypted_analysis
            db.session.commit()  
            flash('日记添加成功', 'success')
            return redirect(url_for('index'))
    return render_template('index.html')


@bp.route('/delete/<int:diary_id>', methods=['GET', 'POST'])
@login_required
def delete(diary_id):
    diary = DiaryModel.query.get(diary_id)
    if diary and diary.author_id == current_user.id:
        db.session.delete(diary)
        db.session.commit()
        user = UserModel.query.get(current_user.id)
        db.session.commit()
        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))

@bp.route('/weekly_report')
@login_required
def week_report():
    report = WeeklyModel.query.filter_by(author_id=current_user.id).order_by(WeeklyModel.create_time.desc()).all()
    return render_template('index.html', report=report)