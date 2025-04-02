# 1. 基础配置和工具函数
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import DiaryModel, UserModel, WeeklyModel
from flask_login import current_user, login_required
from exts import db
from LLM.llm import EmotionAnalyzer  
from datetime import datetime
from utils.crypto import AESCipher
import json
import os
from dotenv import load_dotenv

# 初始化
load_dotenv()
bp = Blueprint('diary', __name__, url_prefix='/diary')
cipher = AESCipher(key=os.getenv("AES_KEY").encode())

# 2. 日记CRUD操作
# 2.1 创建日记
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

# 2.2 查看日记
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

@bp.route('/<int:diary_id>')
@login_required
def diary_detail(diary_id):
    diary = DiaryModel.query.get(diary_id)
    if diary and diary.author_id == current_user.id:
        # 解密日记内容
        decrypted_content = cipher.decrypt(diary.content)
        
        # 检查是否有分析结果
        if diary.analyze:
            decrypted_analysis = json.loads(cipher.decrypt(diary.analyze))
            return render_template('diary_detail.html', 
                diary={
                    'id': diary.id,
                    'title': diary.title,
                    'content': decrypted_content,
                    'create_time': diary.create_time,
                    'analyze': decrypted_analysis
                },
                analysis=decrypted_analysis
            )
        else:
            return render_template('diary_only_content.html',  
                diary={
                    'id': diary.id,
                    'title': diary.title,
                    'content': decrypted_content,
                    'create_time': diary.create_time
                }
            )
    else:
        flash('日记不存在或无权访问')
        return redirect(url_for('diary.mine'))

# 2.3 删除日记
@bp.route('/delete/<int:diary_id>', methods=['GET', 'POST'])
@login_required
def delete(diary_id):
    diary = DiaryModel.query.get(diary_id)
    if diary and diary.author_id == current_user.id:
        db.session.delete(diary)
        db.session.commit()
        analyze = EmotionAnalyzer(f"U{current_user.id}")
        delete_analysis = analyze.delete_diary(diary.datetime)
        flash('日记删除成功')
        
        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))

# 3. 日记分析功能
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
            analysis_result = analyzer.analyze("daily", decrypted_content, diary.create_time)
            
            
            # 加密并保存分析结果
            encrypted_analysis = cipher.encrypt(json.dumps(analysis_result))
            diary.analyze = encrypted_analysis
            diary.emotion_type = analysis_result.get('emotion_type', [])
            db.session.commit()
            
            return jsonify(success=True, analysis=analysis_result)
        except Exception as e:
            db.session.rollback()
            return jsonify(success=False, message=str(e)), 500
    else:
        return jsonify(success=False, message="日记不存在或无权访问"), 403


# 4. 周报相关功能
# 4.1 查看周报
# 获取当前用户的所有阶段性总结报告，按创建时间倒序排列
@bp.route('/weekly_reports')
@login_required
def weekly_report():
    weekly_reports = WeeklyModel.query.filter_by(author_id=current_user.id).order_by(WeeklyModel.start_date.desc()).all()
    return render_template('weekly_reports.html',reports = weekly_reports)

# 展示指定阶段性总结报告详情的路由
@bp.route('/weekly_report_detail/<int:report_id>')
@login_required
def weekly_report_detail(report_id):
    report = WeeklyModel.query.get(report_id)
    if report and report.author_id == current_user.id:
        # 解密报告内容
        decrypted_content = cipher.decrypt(report.content)
        return render_template('weekly_report.html',report = report,content = decrypted_content)
    else:
        flash('报告不存在或无权访问')
        return redirect(url_for('diary.weekly_reports'))
#4.2 生成周报
# 生成阶段性总结报告的路由
@bp.route('/generate_weekly_report', methods=['POST','GET'])
@login_required
def generate_weekly_report():
    if request.method == 'POST':
        try:
            # 解析日期参数
            start_date = request.form.get('start_time')
            end_date = request.form.get('end_time')
            
            if not start_date or not end_date:
                return jsonify(success=False, message="必须提供开始和结束日期"), 400
                
            if start_date > end_date:
                return jsonify(success=False, message="开始日期不能晚于结束日期"), 400

            # 统一使用相同的日期格式
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

            # 获取该时间范围内的日记数量
            diary_count = DiaryModel.query.filter(
                DiaryModel.author_id == current_user.id,
                DiaryModel.create_time >= start_date,
                DiaryModel.create_time <= end_date
            ).count()

            # 生成周报内容
            analyzer = EmotionAnalyzer(f"U{current_user.id}")
            report_data = analyzer.analyze('weekly', start_date, end_date)  
            
            # 加密存储到数据库
            encrypted_report = cipher.encrypt(json.dumps(report_data))
            new_report = WeeklyModel(
                author_id=current_user.id,  # 修正字段名
                content=encrypted_report,
                start_date=start_date.date(),  
                end_date=end_date.date(), 
                diary_nums=diary_count     
            )
            db.session.add(new_report)
            db.session.commit()

            return jsonify(
                success=True,
                message="周报生成成功",
                redirect=url_for('diary.weekly_report_detail', report_id=new_report.id)
            )
            
        except ValueError:
            return jsonify(success=False, message="日期格式应为YYYY-MM-DD"), 400
        except Exception as e:
            db.session.rollback()
            return jsonify(success=False, message=str(e)), 500

# 4.3 删除周报
@bp.route('/delete_weekly_report/<int:report_id>', methods=['GET', 'POST'])
@login_required
def delete_weekly_report(report_id):
    report = WeeklyModel.query.get(report_id)
    if report and report.author_id == current_user.id:
        db.session.delete(report)
        db.session.commit()
        flash('阶段性总结报告删除成功')
        return redirect(url_for('diary.weekly_reports'))
    else:
        return redirect(url_for('diary.weekly_reports'))

# 5. 搜索功能
# 5.1 按情绪搜索
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

# 按关键词搜索日记
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

# 按日期搜索日记
@bp.route('/search_by_date/<date_str>', methods=['GET'])
@login_required
def search_by_date(date_str):
    try:
        # 解析日期字符串
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # 获取当前用户在指定日期创建的日记
        diaries = DiaryModel.query.filter(
            DiaryModel.author_id == current_user.id,
            db.func.date(DiaryModel.create_time) == target_date
        ).order_by(DiaryModel.create_time.desc()).all()
        
        # 解密日记内容
        filtered_diaries = []
        for diary in diaries:
            decrypted_content = cipher.decrypt(diary.content)
            decrypted_analysis = json.loads(cipher.decrypt(diary.analyze)) if diary.analyze else None
            filtered_diaries.append({
                'id': diary.id,
                'title': diary.title,
                'content': decrypted_content,
                'analyze': decrypted_analysis,
                'create_time': diary.create_time
            })
        
        return render_template('index.html', diaries=filtered_diaries)
    except ValueError:
        flash("日期格式无效，请使用YYYY-MM-DD格式")
        return redirect(url_for('diary.mine'))
    except Exception as e:
        flash(f"查询失败: {str(e)}")
        return redirect(url_for('diary.mine'))