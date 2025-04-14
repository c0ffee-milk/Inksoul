# 1. 基础配置和工具函数
# 1.1 标准库导入
import re
import json
import os
import calendar
import time
from datetime import datetime, timedelta
from collections import defaultdict

# 1.2 第三方库导入
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user, login_required
from flask_wtf import form
from dotenv import load_dotenv

# 1.3 本地模块导入
from models import DiaryModel, UserModel, WeeklyModel
from exts import db
from LLM.llm import EmotionAnalyzer
from utils.crypto import AESCipher
from .forms import TimeForm


# 1.4 初始化
load_dotenv()
bp = Blueprint('diary', __name__, url_prefix='/diary')
cipher = AESCipher(key=os.getenv("AES_KEY").encode())

# 2. 日记CRUD操作
# 2.1 创建日记
# 在需要记录日记的地方（比如add路由中）
@bp.route('/add', methods=['POST'])
@login_required
def add():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        if not title or not content:
            return jsonify(success=False, message="日记和标题不能为空"), 400

        try:
            # 创建分析器实例
            analyzer = EmotionAnalyzer(f"U{current_user.id}")
            
            # 先创建日记对象获取统一时间
            diary = DiaryModel(
                title=title,
                content='',  # 临时占位，后面会更新
                author_id=current_user.id
            )
            db.session.add(diary)
            db.session.flush()  # 生成create_time但不提交事务
            
            # 记录日记到向量数据库(使用与SQL数据库相同的时间戳)
            create_time_str = diary.create_time.strftime('%Y-%m-%d %H:%M:%S')
            analyzer.log_diary(text=f"[{create_time_str}]\n{content}", timestamp=int(diary.create_time.timestamp()))
            
            # 加密并更新日记内容
            encrypted_content = cipher.encrypt(content)
            diary.content = encrypted_content
            db.session.commit()
            return jsonify(success=True, message="日记添加成功", redirect=url_for('diary.mine'))
        except Exception as e:
            db.session.rollback()
            return jsonify(success=False, message=str(e)), 500



@bp.route('/mine')
@login_required
def mine():
    # 获取所有日记
    diaries = DiaryModel.query.filter_by(author_id=current_user.id).order_by(DiaryModel.create_time.desc()).all()

    # 解密日记内容
    decrypted_diaries = []
    for diary in diaries:
        decrypted_content = cipher.decrypt(diary.content).replace('\n', '<br>')
        decrypted_analysis = json.loads(cipher.decrypt(diary.analyze)) if diary.analyze else None
        decrypted_diaries.append({
            'id': diary.id,
            'title': diary.title,
            'content': decrypted_content,
            'analyze': decrypted_analysis,
            'create_time': diary.create_time,
            'is_analyzed': diary.is_analyzed  # 添加 is_analyzed 状态
        })

    # ========== 热力图数据生成逻辑 ==========
    # 获取当前月份信息
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    _, days_in_month = calendar.monthrange(current_year, current_month)

    # 统计每日日记数量
    daily_counts = defaultdict(int)
    for diary in diaries:
        if diary.create_time.year == current_year and diary.create_time.month == current_month:
            day = diary.create_time.day
            daily_counts[day] += 1

    # 计算颜色梯度（浅紫#e6e6fa -> 深紫#4b0082）
    max_count = max(daily_counts.values()) if daily_counts else 1
    heatmap_data = []

    for day in range(1, days_in_month + 1):
        if daily_counts.get(day, 0)>5:
            count = 5
        else:
            count = daily_counts.get(day,0)
        # 计算颜色强度（0~1）
        intensity = count / 2.7

        # RGB分量计算
        base_r, base_g, base_b = 230, 230, 250  # #e6e6fa
        target_r, target_g, target_b = 106, 0, 181  # #4b0082

        r = int(base_r + (target_r - base_r) * intensity)
        g = int(base_g + (target_g - base_g) * intensity)
        b = int(base_b + (target_b - base_b) * intensity)

        heatmap_data.append({
            "day": day,
            "count": count,
            "color": f"rgb({r}, {g}, {b})",
            "tooltip": f"{day}日：{count}篇日记"
        })

    # ========== 结束热力图逻辑 ==========

    return render_template('index.html',
                           diaries=decrypted_diaries,
                           heatmap=heatmap_data,  # 新增参数
                           current_month=f"{current_year}-{current_month:02d}")

@bp.route('/<int:diary_id>')
@login_required
def diary_detail(diary_id):
    diary = DiaryModel.query.get(diary_id)
    if diary and diary.author_id == current_user.id:
        # 解密日记内容，确保正常展示分行
        decrypted_content = cipher.decrypt(diary.content).replace('\n', '<br>') 
        
        # 检查是否有分析结果
        # 如果有分析结果，显示分析结果
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
        #如果没有分析结果，只显示内容
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
        if diary.analyze:
            analyze = EmotionAnalyzer(f"U{current_user.id}")
            timestamp = int(diary.create_time.timestamp())
            # 同时删除向量数据库中的日记数据
            delete_analysis = analyze.delete_diary(timestamp)

        db.session.delete(diary)
        db.session.commit()
        flash('日记删除成功')
        return redirect(url_for('diary.mine'))
    else:
        return redirect(url_for('diary.mine'))

# 3. 日记分析功能
@bp.route('/<int:diary_id>/analyze', methods=['POST','GET'])
@login_required
def diary_analyze(diary_id):

        # 设置最大重试次数为3次
    max_retries = 3
    # 设置每次重试的延迟时间为0.5秒
    retry_delay = 0.5  # 0.5秒
    
    # 开始重试循环
    for attempt in range(max_retries):
        # 尝试获取日记对象
        diary = DiaryModel.query.get(diary_id)
        # 如果日记不存在
        if diary is None:
            # 如果还有剩余重试次数
            if attempt < max_retries - 1:
                # 等待指定延迟时间后继续重试
                time.sleep(retry_delay)
                continue
            # 如果已达到最大重试次数，返回404错误
            return "日记不存在", 404
            
        if diary and diary.author_id == current_user.id:
            try:
                # 解密日记内容
                decrypted_content = cipher.decrypt(diary.content)
                
                # 进行情感分析
                user_id = f"U{current_user.id}"
                analyzer = EmotionAnalyzer(user_id)
                timestamp = int(diary.create_time.timestamp())
                analysis_result = analyzer.analyze("daily", decrypted_content, timestamp)
                
                # 加密并保存分析结果
                encrypted_analysis = cipher.encrypt(json.dumps(analysis_result))
                diary.analyze = encrypted_analysis
                diary.emotion_type = analysis_result.get('emotion_type', [])
                diary.is_analyzed = True
                db.session.commit()
                
                return jsonify(success=True, analysis=analysis_result),200
            except Exception as e:
                db.session.rollback()
                return jsonify(success=False, message=str(e)), 500
        else:
            return jsonify(success=False, message="日记不存在或无权访问"), 403
    
    return jsonify(success=False, message="日记数据尚未准备好，请稍后再试"), 503


# 4. 周报相关功能
# 4.1 查看周报
# 获取当前用户的所有阶段性总结报告，按创建时间倒序排列
@bp.route('/weekly_reports')
@login_required
def weekly_reports():
    # 获取所有周报并按时间倒序排列
    weekly_reports = WeeklyModel.query.filter_by(author_id=current_user.id) \
        .order_by(WeeklyModel.start_time.desc()).all()

    # 解密基础信息（不需要解密完整内容）
    reports = []
    for report in weekly_reports:
        reports.append({
            "id": report.id,
            "start": report.start_time.strftime('%Y-%m-%d'),
            "end": report.end_time.strftime('%Y-%m-%d'),
            "diary_count": report.diary_nums
        })

    return render_template('weekly_reports.html', reports=reports)

# 展示指定阶段性总结报告详情的路由
@bp.route('/weekly_report_detail/<int:report_id>')
@login_required
def weekly_report_detail(report_id):
    report = WeeklyModel.query.get(report_id)
    if report and report.author_id == current_user.id:
        # 解密报告内容
        decrypted_content = json.loads(cipher.decrypt(report.content))
        return render_template('weekly_report_detail.html',report = report,content = decrypted_content)
    else:
        flash('报告不存在或无权访问')
        return redirect(url_for('diary.weekly_reports'))

#4.2 生成周报
# 生成阶段性总结报告的路由
@bp.route('/generate_weekly_report', methods=['POST','GET'])
@login_required
def generate_weekly_report():
    form = TimeForm(request.form)
    if form.validate_on_submit():
        try:
            # 验证表单输入
            if not form.start_time.data or not form.end_time.data:
                return jsonify(success=False, message="起始日期和终止日期不能为空"), 400
                
            try:
                start_date = datetime.strptime(form.start_time.data, '%Y-%m-%d')
                end_date = datetime.strptime(form.end_time.data, '%Y-%m-%d') + timedelta(days=1)
            except ValueError as e:
                return jsonify(success=False, message=f"Invalid date format: {str(e)}"), 400

            # 获取该时间范围内的日记数量
            diary_count = DiaryModel.query.filter(
                DiaryModel.author_id == current_user.id,
                DiaryModel.create_time >= start_date,
                DiaryModel.create_time < end_date
            ).count()

            # 检查是否有日记记录
            if diary_count == 0:
                return jsonify(success=False, message="该时间段内没有日记记录"), 400


            # 生成周报内容
            analyzer = EmotionAnalyzer(f"U{current_user.id}")
            report_data = analyzer.analyze(mode='weekly', start_date=start_date, start_date=start_date)  
            
            # 加密存储到数据库
            encrypted_report = cipher.encrypt(json.dumps(report_data))
            new_report = WeeklyModel(
                author_id=current_user.id,  
                content=encrypted_report,
                start_time=start_date,  
                 end_time=end_date - timedelta(days=1),  # 确保结束时间是前一天
                diary_nums=diary_count     
            )
            db.session.add(new_report)
            db.session.commit()
            
            # 添加短暂延迟确保数据库操作完成
            import time
            time.sleep(1)  # 等待1秒

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
            if diary.analyze:
                # 确保先解密并解析JSON
                analysis = json.loads(cipher.decrypt(diary.analyze))
                if emotion_type in analysis.get('emotion_type', []):
                    decrypted_content = cipher.decrypt(diary.content)
                    filtered_diaries.append({
                        'id': diary.id,
                        'title': diary.title,
                        'content': decrypted_content,
                        'analyze': analysis,  # 使用已解析的分析结果
                        'create_time': diary.create_time,
                        'is_analyzed': diary.is_analyzed  # 添加 is_analyzed 状态
                    })
        result_count = len(filtered_diaries)
        return render_template('index.html', diaries=filtered_diaries,
                                             is_search = True,
                                             search_type = 'emotion',
                                             emotion_type = emotion_type,
                                             result_count = result_count)                                           # 改为渲染模板
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
                    'create_time': diary.create_time,
                    'is_analyzed': diary.is_analyzed  # 添加 is_analyzed 状态
                })
        
        # 计算搜索结果数量
        result_count = len(filtered_diaries)
        return render_template('index.html', 
                           diaries=filtered_diaries, 
                           is_search=True, 
                           search_type='keyword',  # 新增搜索类型参数
                           keyword=keyword,
                           result_count=result_count)  # 新增结果数量参数
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
                'create_time': diary.create_time,
                'is_analyzed': diary.is_analyzed  # 添加 is_analyzed 状态
            })
        result_count = len(filtered_diaries)
        return render_template('index.html', diaries=filtered_diaries,
                                             is_search = True,
                                             search_type = 'date',
                                             target_date = target_date,
                                             result_count = result_count )
    except ValueError:
        flash("日期格式无效，请使用YYYY-MM-DD格式")
        return redirect(url_for('diary.mine'))
    except Exception as e:
        flash(f"查询失败: {str(e)}")
        return redirect(url_for('diary.mine'))