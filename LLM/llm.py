from datetime import datetime, timedelta
from typing import Literal
from .zhipuai_embedding import ZhipuAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import json
import time
import re
import os
import logging
from logging import Logger


os.environ["LANGCHAIN_DISABLE_PYDANTIC_WARNINGS"] = "1"

# 配置参数
ZHIPUAI_API_KEY = "54c07d89321b45a6a917ba058252ab72.XvqOIXx1iXJk8wUe"
DEEPSEEK_API_KEY = "sk-9d1358520abf4903824290625d7ffdc3"

# ================== 增强型数据库管理器 ==================
class VectorDBManager:
    def __init__(self):
        self.embedding = ZhipuAIEmbeddings(zhipuai_api_key=ZHIPUAI_API_KEY)
        
    def get_knowledge_db(self) -> Chroma:
        """心理学知识库（长期存储）"""
        return Chroma(
            persist_directory='data_base/knowledge_db',
            embedding_function=self.embedding,
            collection_name="knowledge"
        )
    
    def get_diary_db(self, user_id: str) -> Chroma:
        """用户日记库（基于用户隔离）"""
        # 创建用户专属目录
        base_dir = os.path.abspath('data_base/diary_db')
        user_dir = os.path.join(base_dir, user_id)
        
        # 调试输出路径信息
        print(f"[DEBUG] 正在创建/访问用户目录：{user_dir}")

        os.makedirs(user_dir, exist_ok=True)
        
        # 验证目录权限
        if not os.access(user_dir, os.W_OK):
            raise PermissionError(f"无写入权限：{user_dir}")
        
        return Chroma(
            persist_directory=user_dir,
            embedding_function=self.embedding,
            collection_name=f"diary_{user_id}"  # 确保集合名称唯一
        )



# ================== 智能分析引擎 ==================
class EmotionAnalyzer:
    def __init__(self, user_id: str):
        self.user_id = user_id
        
        # 验证用户ID格式
        if not re.match(r"^U\d+$", self.user_id):
            raise ValueError("用户ID格式应为 U+数字")
        
         # 新增日志配置
        self.logger = logging.getLogger(f"EmotionAnalyzer.{user_id}")
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not self.logger.handlers:  
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.db = VectorDBManager()
        self.llm = ChatOpenAI(
            temperature=0,
            openai_api_key=DEEPSEEK_API_KEY,
            model_name="deepseek-chat",
            base_url="https://api.deepseek.com"
        )
        
        # 初始化带用户隔离的日记库
        self.knowledge_db = self.db.get_knowledge_db()
        self.diary_db = self.db.get_diary_db(self.user_id)  # 传入用户ID

        # 添加存在性检查
        assert os.path.exists(self.diary_db._persist_directory), "用户数据库目录未创建"

        
        # 双模式提示模板
        self.templates = {
            "daily": PromptTemplate(
                input_variables=["knowledge", "current_diary"],

                template="""您是情绪分析专家，基于Robert Plutchik情感轮盘理论和当代复合情绪研究模型，对用户日记进行结构化心理分析：

                
                【专业知识】
                {knowledge}
                
                【用户当日日记】
                {current_diary}
                
                请输出JSON格式包含：
                1. 综合分析用户当日日记：overall_analysis(综合分析)
                2. 喜悦、信任、害怕、惊讶、难过、厌恶、生气、期待这八种基本感情的组成含量（0-100%）:emotional_basis(情感构成）
                3. 根据这几种基本情感的含量与组合效果和原文本细致分析出几个复合情绪的种类：emotion_type（情绪类型）
                4. 在原文中提取当日事件的关键词：keywords（3-5个关键词）
                5. 根据用户的当日情绪，在以下几个方面中选择其中几个提出一些心理建议：音乐推荐、电影/书籍推荐、活动建议（如“今天适合散步”）、心理调节小技巧（如呼吸练习）。immediate_suggestion（即时建议）
                6. 
                """
            ),

            "weekly": PromptTemplate(
                input_variables=["knowledge", "diaries"],
                template="""基于过去一周的日记进行周期性分析：
                
                【心理学理论】
                {knowledge}
                
                【日记记录】
                {diaries}
                
                请输出JSON包含：
                1. 喜悦、信任、害怕、惊讶、难过、厌恶、生气、期待这八种基本感情的组成含量（0-100%）:emotional_basis(情感构成）
                2. 提取这段时间内每天（不用给出日期）的主导事件和主导情绪：domain_event(主导事件)、domain_emotion(主导情绪)
                3. 这段时间的情绪变化趋势：emotion_trend（情绪变化趋势描述）
                4. 针对这段时间的情绪提出专业心理建议：weekly_advice（长期建议）
                5. 总结这段时间的主导事件找出5-10个事件关键词：event_key_words
                6. 总结这段时间的主导情绪找出5-10个情绪关键词：emotion_key_words
                7. 找一段名人的名言，作为总结的引言：famous_quote
                """
            )
        }

    def _get_time_range(self, start: datetime = None, end: datetime = None, days: int = 7) -> dict:
        end = end or datetime.now()
        start = start or (end - timedelta(days=days))
        return {
            "$and": [
                {"date": {"$gte": start.timestamp()}},
                {"date": {"$lte": end.timestamp()}}
            ]
        }

    def safe_retrieve(self, collection, query: str, k: int, filter_: dict = None) -> list:
        """安全检索方法"""
        try:
            # 添加类型检查
            if hasattr(collection, '_collection'):
                total = collection._collection.count()
            elif hasattr(collection, 'vectorstore'):
                # 处理检索器对象的情况
                total = collection.vectorstore._collection.count()
            else:
                raise ValueError("不支持的集合类型")

            adjusted_k = min(k, total) if total > 0 else 0
            if adjusted_k <= 0:
                return []

            return collection.max_marginal_relevance_search(
                query=query,
                k=adjusted_k,
                filter=filter_
            )
        except Exception as e:
            print(f"检索失败: {str(e)}")
            return []



    def _retrieve_diaries(self, mode: Literal["daily", "weekly"], 
                     query: str = None, start: datetime = None, 
                     end: datetime = None, days: int = None) -> str:
        # 添加用户过滤条件
        base_filter = {"user_id": self.user_id}
        
        if mode == "daily":
            time_filter = self._get_time_range(days=1)
        else:
            # 当weekly模式时优先使用自定义参数
            time_filter = self._get_time_range(
                start=start, 
                end=end,
                days=days if days else 7  # 保持默认7天
            )
        
        combined_filter = {"$and": [base_filter, time_filter]}
        
        if mode == "daily":
            docs = self.safe_retrieve(self.diary_db, query, 3, combined_filter)
        else:
            docs = self.safe_retrieve(self.diary_db, "总结本周情绪", 50, combined_filter)
        
        return "\n".join([d.page_content for d in docs]) if docs else "无日记记录"


    def log_diary(self, text: str, date: datetime = None):
        """保存单条日记到向量数据库
        :param date: 可选日期参数，默认为当前时间
        """

        try:
            if date and not isinstance(date, datetime):
                raise ValueError("date参数必须是datetime类型")
            timestamp = date.timestamp() if date else datetime.now().timestamp()

            # 检查是否存在相似日记
            existing = self.diary_db.similarity_search(text, k=1)
            if existing and existing[0].page_content == text:
                self.logger.warning("[WARNING] 检测到重复日记，跳过保存")
                return

            # 添加日记到数据库
            self.diary_db.add_texts(
                texts=[text],
                metadatas=[{
                    "user_id": self.user_id,
                    "date": timestamp,
                    "source": "user_diary"
                }]
            )
            self.diary_db.persist()  # 确保立即持久化
            self.logger.info(f"[SUCCESS] 日记已保存: {text[:20]}...")
        except Exception as e:
            self.logger.error(f"[ERROR] 保存失败: {str(e)}")


    def get_diary_dates(self) -> list:
        """获取用户所有日记的日期列表（按时间排序）"""
        try:
            # 获取所有元数据
            collection = self.diary_db.get()
            metadatas = collection.get('metadatas', [])
            
            # 提取并转换时间戳
            dates = []
            for meta in metadatas:
                if 'date' in meta:
                    dt = datetime.fromtimestamp(meta['date'])
                    dates.append(dt.strftime("%Y-%m-%d"))  # 格式化为日期字符串
                    
            # 去重并排序
            unique_dates = sorted(list(set(dates)), 
                                key=lambda x: datetime.strptime(x, "%Y-%m-%d"))
            return unique_dates
            
        except Exception as e:
            self.logger.error(f"[ERROR] 获取日期失败: {str(e)}")
            return []


    def analyze(self, mode: Literal["daily", "weekly"], diary: str = None, date: datetime = None, start_date: datetime = None, end_date: datetime = None) -> dict:
    


        """执行分析（双模式入口）"""
        # 知识检索（不同模式使用不同查询策略）
        knowledge_query = "情绪分析" if mode == "daily" else "长期情绪分析与管理"
        knowledge_retriever = self.knowledge_db.as_retriever(search_kwargs={"k": 5})
        real_knowledge_store = knowledge_retriever.vectorstore
        knowledge_docs = self.safe_retrieve(real_knowledge_store, knowledge_query, 5)
        knowledge_context = "\n".join([d.page_content for d in knowledge_docs]) if knowledge_docs else "暂无专业知识"
        
        if mode == "daily" and diary:
            self.log_diary(diary, date=date)

        # 日记处理
        if mode == "daily":
            diary_context = self._retrieve_diaries("daily", query=diary)
            prompt = self.templates["daily"].format(
                knowledge=knowledge_context,
                current_diary=diary
            )
        else:
            diary_context = self._retrieve_diaries(
                "weekly", 
                start=start_date,
                end=end_date
            )
            prompt = self.templates["weekly"].format(
                knowledge=knowledge_context,
                diaries=diary_context
            )
        
        # 调用模型并解析
        response = self.llm.invoke(prompt)
        try:
            return json.loads(response.content.strip("```json").strip())
        except:
            return {"error": "分析结果解析失败"}