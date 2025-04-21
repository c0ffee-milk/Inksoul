# Inksoul - 情感日记与智能分析平台

## 项目概述
Inksoul是一个基于AI的情感日记平台，结合了现代心理学理论和大模型技术，为用户提供安全、私密的日记记录和智能情感分析体验。平台支持日常情绪分析和周期性情绪报告，通过可视化呈现用户的情绪变化趋势，帮助用户更好地理解自己的情绪状态。

## 核心功能
- 加密日记记录：使用AES-256-CBC加密技术保护用户日记内
- 情感智能分析：基于Robert Plutchik情感轮盘理论的多维度情绪分析
- 周期报告生成：自动生成包含情绪趋势、关键事件和个性化建议的周期报告
- 可视化情绪追踪：通过热力图、雷达图等直观展示情绪变化
- 检索与回顾：支持按情绪类型、关键词和日期检索历史日记

## 技术架构
- 后端：Flask框架、SQLAlchemy ORM
- 数据库：MySQL (结构化数据)、Chroma (向量数据)
- AI引擎：基于大模型API (智谱AI、DeepSeek、通义)
- 安全层：AES加密、Flask-Login认证、CSRF保护
- 前端：Jinja2模板、Bootstrap5、ECharts可视化

## 情感分析特点
- 基于8种基本情绪（喜悦、信任、害怕、惊讶、难过、厌恶、生气、期待）的定量分析
- 复合情绪识别与标签生成
- 情绪类型分类（振奋、愉悦、平和、焦虑、低落、烦闷）
- 个性化建议（音乐、书籍、活动、调节技巧）
- 历史情感关联与文化引用

## 安装部署
1. 克隆仓库
```bash
git clone git@github.com:c0ffee-milk/web_for_Inksoul.git
cd web_for_Inksoul
```
2. 安装依赖
```bash
pip install -r requirements.txt
```
3. 创建环境变量文件(.env)
```text
FLASK_SECRET_KEY=your_secret_key
AES_KEY=your_aes_key
ZHIPUAI_API_KEY=your_zhipuai_key
DEEPSEEK_API_KEY=your_deepseek_key
TONGYI_API_KEY=your_tongyi_key
ENCRYPTION_KEY=your_encryption_key
```
4. 初始化数据库
```bash
flask db init
flask db migrate
flask db upgrade
```
5. 运行应用
```bash
python app.py
```

## 技术亮点
- 双数据库架构：结构化数据与向量数据的协同管理
- 全链路加密：从传输到存储的端到端安全保障
- RAG增强生成：基于知识库和用户历史数据的检索增强生成
- 情绪多维分析：基于心理学理论的复合情绪量化模型
- 用户数据隔离：严格的用户数据分离机制

## 项目展望
- 跨平台移动应用支持
- 情绪分析模型本地化部署
- 社区心理资源整合
- 长期情绪健康趋势预测
