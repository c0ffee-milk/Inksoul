# Inksoul - 情感日记与智能分析平台

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)
![Status](https://img.shields.io/badge/status-stable-green)

<div align="center">
    <img src="static/image.svg" alt="Inksoul Logo" width="200" height="200">
</div>

## 📖 项目概述

Inksoul是一个基于AI的情感日记平台，结合了现代心理学理论和大模型技术，为用户提供安全、私密的日记记录和智能情感分析体验。平台支持日常情绪分析和周期性情绪报告，通过可视化呈现用户的情绪变化趋势，帮助用户更好地理解自己的情绪状态。



## ✨ 核心功能

- **加密日记记录**：使用AES-256-CBC加密技术保护用户日记内容
- **情感智能分析**：基于Robert Plutchik情感轮盘理论的多维度情绪分析
- **周期报告生成**：自动生成包含情绪趋势、关键事件和个性化建议的周期报告
- **可视化情绪追踪**：通过热力图、雷达图等直观展示情绪变化
- **检索与回顾**：支持按情绪类型、关键词和日期检索历史日记

## 🔧 技术架构

- **后端**：Flask框架、SQLAlchemy ORM
- **数据库**：MySQL (结构化数据)、Chroma (向量数据)
- **AI引擎**：基于大模型API (智谱AI、DeepSeek、通义)
- **安全层**：AES加密、Flask-Login认证、CSRF保护
- **前端**：Jinja2模板、Bootstrap5、ECharts可视化

## 🧠 情感分析特点

- 基于8种基本情绪（喜悦、信任、害怕、惊讶、难过、厌恶、生气、期待）的定量分析
- 复合情绪识别与标签生成
- 情绪类型分类（振奋、愉悦、平和、焦虑、低落、烦闷）
- 个性化建议（音乐、书籍、活动、调节技巧）
- 历史情感关联与文化引用

## 🚀 快速开始

### 前置条件

- Python 3.9+
- MySQL 5.7+
- 智谱AI/DeepSeek/通义 API 密钥

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/c0ffee-milk/Inksoul.git
cd Inksoul
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 创建并配置环境变量文件(.env)
```
FLASK_SECRET_KEY=your_secret_key
AES_KEY=your_aes_key
ZHIPUAI_API_KEY=your_zhipuai_key
DEEPSEEK_API_KEY=your_deepseek_key
TONGYI_API_KEY=your_tongyi_key
ENCRYPTION_KEY=your_encryption_key
SQLALCHEMY_DATABASE_URI=mysql+pymysql://username:password@localhost/inksoul
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

6. 访问应用
浏览器打开 http://localhost:80

### 配置说明

- `FLASK_SECRET_KEY`: Flask应用密钥，用于会话安全
- `AES_KEY`: AES加密密钥，用于日记内容加密
- `ZHIPUAI_API_KEY`: 智谱AI API密钥
- `DEEPSEEK_API_KEY`: DeepSeek API密钥
- `TONGYI_API_KEY`: 通义API密钥
- `ENCRYPTION_KEY`: 向量数据库加密密钥
- `SQLALCHEMY_DATABASE_URI`: 数据库连接URI

## 💡 技术亮点

- **双数据库架构**：结构化数据与向量数据的协同管理
- **全链路加密**：从传输到存储的端到端安全保障
- **RAG增强生成**：基于知识库和用户历史数据的检索增强生成
- **情绪多维分析**：基于心理学理论的复合情绪量化模型
- **用户数据隔离**：严格的用户数据分离机制

## 🗂️ 项目结构

```
web_for_Inksoul/
├── app.py              # 应用入口文件
├── setting.py          # 应用配置
├── models.py           # 数据模型
├── exts.py             # 扩展模块
├── routes/             # 路由模块
│   ├── auth.py         # 认证路由
│   ├── diary.py        # 日记路由
│   └── index.py        # 主页路由
├── LLM/                # AI模块
│   └── llm.py          # 大模型接口
├── templates/          # 前端模板
├── static/             # 静态资源
├── utils/              # 工具函数
│   └── crypto.py       # 加密工具
└── data_base/          # 数据库文件
```

## 🔮 项目展望

- 跨平台移动应用支持
- 情绪分析模型本地化部署
- 社区心理资源整合
- 长期情绪健康趋势预测
- 多语言支持

## 👥 贡献指南

欢迎贡献代码、提出问题或建议！

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request
