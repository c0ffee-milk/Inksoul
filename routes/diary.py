from flask import Blueprint, render_template, request, redirect, url_for, flash,jsonify
from models import DiaryModel, UserModel, WeeklyModel
from flask_login import current_user, login_required
from exts import db
from LLM.llm import EmotionAnalyzer  # 新增导入
from datetime import datetime  # 新增导入
from utils.crypto import AESCipher
import json
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

bp = Blueprint('diary', __name__, url_prefix='/diary')

# 在应用启动时初始化加密器，从环境变量读取密钥
cipher = AESCipher(key=os.getenv("AES_KEY").encode())



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
        print(decrypted_analysis)
    return render_template('index.html', diaries=decrypted_diaries)


@bp.route('/add', methods=['POST'])
@login_required
def add():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        if not title or not content:
            return jsonify(success=False, message="日记和标题不能为空"), 400

        try:
            encrypted_content = cipher.encrypt(content)
            diary = DiaryModel(
                title=title,
                content=encrypted_content,
                author_id=current_user.id
            )
            db.session.add(diary)
            db.session.commit()
            return jsonify(success=True, message="日记添加成功", redirect=url_for('diary.mine'))
        except Exception as e:
            db.session.rollback()
            return jsonify(success=False, message=str(e)), 500


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


@bp.route('/<int:diary_id>')
@login_required
def diary_detail(diary_id):
    diary = DiaryModel.query.get(diary_id)
    if diary and diary.author_id == current_user.id:
        # 解密日记内容和分析结果
        decrypted_content = cipher.decrypt(diary.content)
        decrypted_analysis = json.loads(cipher.decrypt(diary.analyze)) if diary.analyze else None
        return render_template('diary_detail.html', 
            diary={
                'id': diary.id,
                'title': diary.title,
                'content': decrypted_content,
                'create_time': diary.create_time,
                'analyze': decrypted_analysis  # 确保传递 analyze 数据
            },
            analysis=decrypted_analysis  # 添加 analysis 变量
        )
    else:
        flash('日记不存在或无权访问')
        return redirect(url_for('diary.mine'))

@bp.route('/<int:diary_id>/analyze', methods=['POST','GET'])
@login_required
def diary_analyze(diary_id):
    diary = DiaryModel.query.get(diary_id)
    if diary and diary.author_id == current_user.id:
        try:
            # 解密日记内容
            decrypted_content = cipher.decrypt(diary.content)
            
            # 进行情感分析
            user_id = f"U{current_user.id}"
            analyzer = EmotionAnalyzer(user_id)
            analysis_result = analyzer.analyze("daily", decrypted_content)
            
            # 加密并保存分析结果
            encrypted_analysis = cipher.encrypt(json.dumps(analysis_result))
            diary.analyze = encrypted_analysis
            db.session.commit()
            
            return jsonify(success=True, analysis=analysis_result)
        except Exception as e:
            db.session.rollback()
            return jsonify(success=False, message=str(e)), 500
    else:
        return jsonify(success=False, message="日记不存在或无权访问"), 403



@bp.route('/search_by_emotion/<emotion_type>', methods=['GET'])
@login_required
def search_by_emotion(emotion_type):
    try:
        # 获取当前用户的所有日记
        diaries = DiaryModel.query.filter_by(author_id=current_user.id).all()
        
        # 过滤出包含指定情绪类型的日记
        filtered_diaries = []
        for diary in diaries:
            if diary.analyze and emotion_type in diary.analyze.get('emotion_type', []):
                decrypted_content = cipher.decrypt(diary.content)
                decrypted_analysis = json.loads(cipher.decrypt(diary.analyze)) if diary.analyze else None
                filtered_diaries.append({
                    'id': diary.id,
                    'title': diary.title,
                    'content': decrypted_content,
                    'analyze': decrypted_analysis,
                    'create_time': diary.create_time
                })
        
        return render_template('index.html', diaries=filtered_diaries)  # 改为渲染模板
    except Exception as e:
        flash(str(e))
        return redirect(url_for('diary.mine'))


@bp.route('/search', methods=['GET'])
@login_required
def search():
    keyword = request.args.get('keyword')
    if not keyword:
        flash("请输入搜索关键词")
        return redirect(url_for('diary.mine'))

    try:
        # 获取当前用户的所有日记
        diaries = DiaryModel.query.filter_by(author_id=current_user.id).all()
        
        # 过滤出包含关键词的日记
        filtered_diaries = []
        for diary in diaries:
            # 解密日记内容
            decrypted_content = cipher.decrypt(diary.content)
            
            # 检查标题或正文是否包含关键词
            if keyword.lower() in diary.title.lower() or keyword.lower() in decrypted_content.lower():
                decrypted_analysis = json.loads(cipher.decrypt(diary.analyze)) if diary.analyze else None
                filtered_diaries.append({
                    'id': diary.id,
                    'title': diary.title,
                    'content': decrypted_content,
                    'analyze': decrypted_analysis,
                    'create_time': diary.create_time
                })
        
        return render_template('index.html', diaries=filtered_diaries)  # 改为渲染模板
    except Exception as e:
        flash(str(e))
        return redirect(url_for('diary.mine'))