from datetime import datetime, timedelta
from typing import Literal
from zhipuai_embedding import ZhipuAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import json
import time
import re
import os


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
            persist_directory='../data_base/knowledge_db',
            embedding_function=self.embedding,
            collection_name="knowledge"
        )
    
    def get_diary_db(self) -> Chroma:
        return Chroma(
            persist_directory='../data_base/diary_db',
            embedding_function=self.embedding,
            collection_name="diary"
        )


# ================== 智能分析引擎 ==================
class EmotionAnalyzer:
    def __init__(self):
        self.db = VectorDBManager()
        self.llm = ChatOpenAI(
            temperature=0.5,
            openai_api_key=DEEPSEEK_API_KEY,
            model_name="deepseek-reasoner",
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
        if mode == "daily":
            filter_ = self._get_time_range(1)
            docs = self.safe_retrieve(self.diary_db, query, 3, filter_)

            return "\n".join([d.page_content for d in docs]) if docs else "当日无日记"
        else:
            # 实现 weekly 逻辑
            filter_ = self._get_time_range(7)
            docs = self.safe_retrieve(self.diary_db, "总结本周情绪", 50, filter_)
            return "\n".join([d.page_content for d in docs][:15]) if docs else "本周无日记"


    def analyze(self, mode: Literal["daily", "weekly"], diary: str = None) -> dict:

        """执行分析（双模式入口）"""
        # 知识检索（不同模式使用不同查询策略）
        knowledge_query = "情绪分析" if mode == "daily" else "长期情绪分析与管理"
        knowledge_retriever = self.knowledge_db.as_retriever(search_kwargs={"k": 2})
        real_knowledge_store = knowledge_retriever.vectorstore
        knowledge_docs = self.safe_retrieve(real_knowledge_store, knowledge_query, 2)
        knowledge_context = "\n".join([d.page_content for d in knowledge_docs]) if knowledge_docs else "暂无专业知识"
        
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
    # 创建存储目录
    os.makedirs('../data_base/knowledge_db', exist_ok=True)
    os.makedirs('../data_base/diary_db', exist_ok=True)
    
    # 初始化空集合
    db_manager = VectorDBManager()
    knowledge_db = db_manager.get_knowledge_db()
    diary_db = db_manager.get_diary_db()
    time.sleep(1)  # 确保初始化完成
    
    # 写入测试数据
    knowledge_db.add_texts(
        texts=["情绪识别技巧：通过语言关键词分析情绪倾向..."],
        metadatas=[{"source": "心理学手册", "date": datetime.now().timestamp()}]
    )
    
    diary_db.add_texts(
        texts=["测试日记：今天心情平静..."],
        metadatas=[{"date": datetime.now().timestamp()}]
    )
    
    # 执行分析
    analyzer = EmotionAnalyzer()
    daily_result = analyzer.analyze(mode="daily", diary="晨起整理抽屉时，翻出三年前那支蒙尘的钢笔。墨囊早已干涸，玻璃瓶里的永生苔却蔓延出绒毛般的绿意，在瓶底洇出两枚硬币大小的潮痕。窗台的绿萝新抽的卷须垂向地板，在晨光里投下细蛇般的影。午后泡茶总忘记关火，铸铁壶在灶上呜咽了半个钟头。翻开读到第137页的《荒原》，发现夹着的银杏叶碎成了齑粉，像被时间蛀空的蝉蜕。书页间抖落的尘埃悬浮在光束里，慢慢沉降成茶几上浅淡的灰圈。日历停在三月的那页，边角被水汽浸得发皱。鱼缸里的斑马鱼贴着玻璃往复游动，尾鳍在缸壁刮出细不可闻的沙响。阳台晾着的白衬衫在风里鼓胀，忽然又坍缩成空荡的躯壳，纽扣磕碰着栏杆叮当作响。暮色沉降时数了十七遍抽屉里的药片，铝箔板上的凹痕排列成模糊的星座。风掠过楼宇间隙送来孩童断续的琴声，某个降调的和弦卡在窗框间震颤。云层裂开的缝隙里漏下稀薄的天光，正巧落在那盆停止开花的茉莉上。茶凉透时，蜗牛沿着玻璃瓶完成了第五次环游，在苔藓表面拖曳出银亮的轨迹。忽然想起该给钢笔换墨囊，却发现瓶底那团绿意里蜷着蜗牛的空壳，像枚被遗落的逗号。")
    print(daily_result)