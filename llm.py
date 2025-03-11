from datetime import datetime, timedelta
from typing import Literal
from zhipuai_embedding import ZhipuAIEmbeddings
from langchain.vectorstores.chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import json

# 配置参数
ZHIPUAI_API_KEY = "54c07d89321b45a6a917ba058252ab72.XvqOIXx1iXJk8wUe"
DEEPSEEK_API_KEY = "sk-9d1358520abf4903824290625d7ffdc3"

# ================== 增强型数据库管理器 ==================
class VectorDBManager:
    def __init__(self):
        self.embedding = ZhipuAIEmbeddings()
        
    def get_knowledge_db(self) -> Chroma:
        """心理学知识库（长期存储）"""
        return Chroma(
            persist_directory='./data_base/knowledge_db',
            embedding_function=self.embedding
        )
    
    def get_diary_db(self) -> Chroma:
        """用户日记库（自动清理过期数据）"""
        return Chroma(
            persist_directory='./data_base/diary_db',
            embedding_function=self.embedding,
            collection_metadata={"hnsw:auto_delete": True}  # 自动清理1周前数据
        )

# ================== 智能分析引擎 ==================
class EmotionAnalyzer:
    def __init__(self):
        self.db = VectorDBManager()
        self.llm = ChatOpenAI(
            temperature=0.5,
            openai_api_key=DEEPSEEK_API_KEY,
            model_name="deepseek-chat",
            base_url="https://api.deepseek.com"
        )
        
        # 初始化双数据库连接
        self.knowledge_db = self.db.get_knowledge_db()
        self.diary_db = self.db.get_diary_db()
        
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
                1. emotion_type（情绪类型）
                2. keywords（3个关键词）
                3. immediate_suggestion（即时建议）"""
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
        """生成时间范围过滤器"""
        end = datetime.now()
        start = end - timedelta(days=days)
        return {
            "date": {
                "$gte": start.strftime("%Y-%m-%d"),
                "$lte": end.strftime("%Y-%m-%d")
            }
        }

    def _retrieve_diaries(self, mode: Literal["daily", "weekly"], query: str = None) -> str:
        """智能日记检索"""
        if mode == "daily":
            # 当日模式：使用当前日记进行相似搜索（发现关联历史记录）
            docs = self.diary_db.max_marginal_relevance_search(
                query=query,
                k=3,
                filter=self._get_time_range(1)  # 当天+相似历史
            )
        else:
            # 周模式：获取全部日记（不依赖搜索）
            docs = self.diary_db.get(
                where=self._get_time_range(7),
                include=["metadatas", "documents"]
            )["documents"]
            
        return "\n".join([
            f"{doc.metadata['date']}: {doc.page_content}" 
            if mode == "weekly" else doc.page_content
            for doc in (docs if mode == "daily" else docs)
        ])

    def analyze(self, mode: Literal["daily", "weekly"], diary: str = None) -> dict:
        """执行分析（双模式入口）"""
        # 知识检索（不同模式使用不同查询策略）
        knowledge_query = "情绪识别技巧" if mode == "daily" else "长期情绪管理"
        knowledge_docs = self.knowledge_db.as_retriever(search_kwargs={"k": 2}).invoke(knowledge_query)
        knowledge_context = "\n".join([d.page_content for d in knowledge_docs])
        
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
    analyzer = EmotionAnalyzer()
    
    # 当日分析模式
    daily_result = analyzer.analyze(
        mode="daily",
        diary="今天被领导表扬了，但同事似乎不太高兴..."
    )
    print("当日分析结果：", daily_result)
    
    # 周分析模式（无需输入日记）
    weekly_result = analyzer.analyze(mode="weekly")
    print("周度分析报告：", weekly_result)
