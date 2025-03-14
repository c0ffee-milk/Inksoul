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
                template="""作为心理分析师，请结合专业知识和当前日记进行分析：
                
                【专业知识】
                {knowledge}
                
                【用户当日日记】
                {current_diary}
                
                请输出JSON包含：
                1.喜悦、信任、害怕、惊讶、难过、厌恶、生气、期待这八种基本感情的组成含量（0-100%）:emotional_basis(情感构成）
                2. 根据这几种基本情感的含量与组合效果和原文本细致分析出几个复合情绪的种类：emotion_type（情绪类型）
                2. 根据情绪种类与原文提炼出跟情绪有关的 （如悲喜交加、遗憾、孤独等）的：keywords（3个关键词）
                3. 根据原文内容提出一些易懂的可以改善负面情绪，调节心理状况的immediate_suggestion（即时建议）"""
            ),
            "weekly": PromptTemplate(
                input_variables=["knowledge", "diaries"],
                template="""基于过去一周的日记进行周期性分析：
                
                【心理学理论】
                {knowledge}
                
                【日记记录】
                {diaries}
                
                请输出JSON包含：
                1. dominant_emotion（主导情绪）
                2. emotion_trend（情绪变化趋势描述）
                3. weekly_advice（长期建议）
                4. significant_events（重要事件列表）"""
            )
        }

    def _get_time_range(self, days: int = 7) -> dict:
        end = datetime.now()
        start = end - timedelta(days=days)
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



    def _retrieve_diaries(self, mode: Literal["daily", "weekly"], query: str = None) -> str:
        # 添加用户过滤条件
        base_filter = {"user_id": self.user_id}
        
        if mode == "daily":
            time_filter = self._get_time_range(1)
            combined_filter = {"$and": [base_filter, time_filter]}
            docs = self.safe_retrieve(self.diary_db, query, 3, combined_filter)
        else:
            time_filter = self._get_time_range(7)
            combined_filter = {"$and": [base_filter, time_filter]}
            docs = self.safe_retrieve(self.diary_db, "总结本周情绪", 50, combined_filter)
        
        return "\n".join([d.page_content for d in docs]) if docs else "无日记记录"


    def log_diary(self, text: str):
        """保存单条日记到向量数据库"""
        try:
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
                    "date": datetime.now().timestamp(),
                    "source": "user_diary"
                }]
            )
            self.diary_db.persist()  # 确保立即持久化
            self.logger.info(f"[SUCCESS] 日记已保存: {text[:20]}...")
        except Exception as e:
            self.logger.error(f"[ERROR] 保存失败: {str(e)}")


    def analyze(self, mode: Literal["daily", "weekly"], diary: str = None) -> dict:


        """执行分析（双模式入口）"""
        # 知识检索（不同模式使用不同查询策略）
        knowledge_query = "情绪分析" if mode == "daily" else "长期情绪分析与管理"
        knowledge_retriever = self.knowledge_db.as_retriever(search_kwargs={"k": 5})
        real_knowledge_store = knowledge_retriever.vectorstore
        knowledge_docs = self.safe_retrieve(real_knowledge_store, knowledge_query, 5)
        knowledge_context = "\n".join([d.page_content for d in knowledge_docs]) if knowledge_docs else "暂无专业知识"
        
        if mode == "daily" and diary:
            self.log_diary(diary)

        # 日记处理
        if mode == "daily":
            diary_context = self._retrieve_diaries("daily", query=diary)
            prompt = self.templates["daily"].format(
                knowledge=knowledge_context,
                current_diary=diary
            )
        else:
            diary_context = self._retrieve_diaries("weekly")
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

# ================== 使用示例 ==================

if __name__ == "__main__":
    # 模拟两个用户
    user_metadata = [
        {"user_id": "U123", "text": "测试用户A的日记..."},
        {"user_id": "U456", "text": "测试用户B的日记..."}
    ]
    for meta in user_metadata:
        # 初始化用户专属数据库
        user_db = VectorDBManager().get_diary_db(meta["user_id"])
        
        # 写入带用户ID的元数据
        user_db.add_texts(
            texts=[meta["text"]],
            metadatas=[{
                "user_id": meta["user_id"],
                "date": datetime.now().timestamp(),
                "source": "user_diary"
            }]
        )

    user_db.persist()
    time.sleep(0.5) 
    
    # 用户A的分析实例
    analyzer_A = EmotionAnalyzer(user_id="U123")
    result_A = analyzer_A.analyze(mode="daily", diary="今天感到有些焦虑")
    print("用户A分析结果:", result_A)

    # 用户B的分析实例
    analyzer_B = EmotionAnalyzer(user_id="U456")
    result_B = analyzer_A.analyze(mode="daily", diary="今天心情愉快")
    print("用户B分析结果:", result_B)