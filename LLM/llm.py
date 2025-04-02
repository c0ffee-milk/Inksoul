from datetime import datetime, timedelta
from typing import Literal
from .zhipuai_embedding import ZhipuAIEmbeddings
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import json
import time
import re
import os
import logging
from logging import Logger
from dotenv import load_dotenv


load_dotenv()  # 加载.env文件
os.environ["LANGCHAIN_DISABLE_PYDANTIC_WARNINGS"] = "1"

# 配置参数
ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
TONGYI_API_KEY = os.getenv("TONGYI_API_KEY")

# ================== 增强型数据库管理器 ==================
class VectorDBManager:
    def __init__(self):
        self.embedding = ZhipuAIEmbeddings(zhipuai_api_key=ZHIPUAI_API_KEY)
        self.logger = logging.getLogger("VectorDBManager")
        self.logger.addHandler(logging.NullHandler())
        
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
    
    def delete_diary_by_timestamp(self, user_id: str, timestamp: float) -> bool:
        """根据精确时间戳删除日记（精确到秒）
        Args:
            user_id: 用户ID
            timestamp: 精确到秒的时间戳
        Returns:
            bool: 是否删除成功
        """
        try:
            diary_db = self.get_diary_db(user_id)
            collection = diary_db._collection
            
            # 精确匹配查询
            query = {
                "$and": [
                    {"user_id": user_id},
                    {"date": int(timestamp)}
                ]
            }

            existing = collection.get(where=query)
            if not existing.get('ids'):
                return False
            
            # 在查询后添加调试日志
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"查询条件：{query}, 找到记录：{len(existing.get('ids', []))}条")
            
            ids_to_delete = existing.get('ids', [])
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)  # 使用 ids 而不是 where 查询
                diary_db.persist()
                return True
            return False
        except Exception as e:
            self.logger.error(f"删除日记失败: {str(e)}", exc_info=True)
            return False




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
            openai_api_key=TONGYI_API_KEY,
            model_name="deepseek-r1",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
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
                3. 根据这几种基本情感的含量与组合效果和原文本细致分析出几个复合情绪的种类：emotion_lable（情绪类型）
                4. 根据用户日记体现的情绪，将本日记分为以下六种中的一种(振奋、愉悦、平和、焦虑、低落、烦闷)：emotion_type（情绪类型）
                5. 在原文中提取当日事件的关键词：keywords（3-5个关键词）
                6. 根据用户的当日情绪，在以下几个方面中选择其中几个提出一些心理建议：音乐推荐、电影/书籍推荐、活动建议（如“今天适合散步”）、心理调节小技巧（如呼吸练习）。immediate_suggestion（即时建议）
                7. 根据用户的经历，从百年文学/电影/历史中抓取相似瞬间，结构类似："1926年海明威在巴黎的雨天同样丢失手稿，他喝了三杯威士忌后继续写作"（强调"也、同样"等表达相似的词，禁止直接引用前面的例子）：history_moment
                
                输出要求：
                1.面向用户输出，注意人称用词必须用您
                2.提出的建议要基于现实，容易实现

                输出格式：
                {{
                    "overall_analysis": "分析内容",
                    "emotional_basis": {{
                        "喜悦": 0-100,
                        "信任": 0-100,
                        "害怕": 0-100,
                        "惊讶": 0-100,
                        "难过": 0-100,
                        "厌恶": 0-100,
                        "生气": 0-100,
                        "期待": 0-100
                    }},
                    "emotion_label": [
                        "label1",
                        "label2",
                        ...
                    ],
                    "emotion_type": "type",
                    "keywords": [
                        "关键词1",
                        "关键词2",
                        "关键词3",
                        "关键词4",
                        "关键词5"
                    ],
                    "immediate_suggestion": {{
                        "music":"音乐推荐与推荐理由1", "音乐推荐与推荐理由2",
                        "books":"书籍推荐与推荐理由",
                        "activities":"活动建议",
                        "techniques":"心理调节技巧"
                    }},
                    "history_moment": "历史回响内容"
                }}
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
                1. 以第二人称讲述的形式回顾用户过去这段时间的经历：diary_review
                2. 喜悦、信任、害怕、惊讶、难过、厌恶、生气、期待这八种基本感情的组成含量（0-100%）:emotional_basis(情感构成）
                3. 提取这段时间内每天（不用给出日期）的主导事件和主导情绪：domain_event(主导事件)、domain_emotion(主导情绪)
                4. 分析这段时间的情绪变化趋势：emotion_trend（情绪变化趋势描述）
                5. 针对这段时间的情绪提出给用户下一周的建议：weekly_advice（长期建议）
                6. 总结这段时间的主导事件找出5-10个事件关键词：event_key_words
                7. 总结这段时间的主导情绪找出5-10个情绪关键词：emotion_key_words
                8. 结合用户这段时间的心理情绪找一段名人的名言，作为总结的引言：famous_quote
                """
            )
        }

    def _get_time_range(self, start: datetime = None, end: datetime = None, days: int = 7) -> dict:
        end = end or datetime.now()
        start = start or (end - timedelta(days=days))
        return {
            "$and": [
                {"date": {"$gte": int(start.timestamp())}},
                {"date": {"$lte": int(end.timestamp())}}
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
        
        combined_filter = {
            "$and": [
                {"user_id": self.user_id},
                time_filter  # time_filter 本身已经是带有 $gte/$lte 的条件
            ]
        }
        
        if mode == "daily":
            docs = self.safe_retrieve(self.diary_db, query, 3, combined_filter)
        else:
            docs = self.safe_retrieve(self.diary_db, "总结本周情绪", 50, combined_filter)
        
        return "\n".join([d.page_content for d in docs]) if docs else "无日记记录"


    def log_diary(self, text: str, timestamp: float = None):
        """保存单条日记到向量数据库（时间戳由后端精确控制）
        Args:
            text: 日记内容
            timestamp: 精确到秒的时间戳（可选，不传则使用当前时间戳）
        """
        try:
            # 强制时间戳精确到秒（去掉毫秒部分）
            timestamp = int(timestamp if timestamp is not None else time.time())
            
            # 检查是否存在相似日记（相同时间戳+相同用户视为重复）
            existing = self.diary_db.similarity_search(
                query=text,
                k=1,
                filter={
                    "$and": [
                        {"user_id": {"$eq": self.user_id}},
                        {"date": {"$eq": timestamp}}
                    ]
                }
            )
            
            if existing and existing[0].page_content == text:
                self.logger.warning(f"[WARNING] 检测到重复日记（时间戳：{timestamp}），跳过保存")
                return

            # 添加日记到数据库
            self.diary_db.add_texts(
                texts=[text],
                metadatas=[{
                    "user_id": self.user_id,
                    "source": "user_diary",
                    "date": int(timestamp)
                }]
            )
            # self.diary_db.persist()
            self.logger.info(f"[SUCCESS] 日记已保存（时间：{datetime.fromtimestamp(timestamp)}）")
        except Exception as e:
            self.logger.error(f"[ERROR] 保存失败: {str(e)}")
            raise

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


    def analyze(self, mode: Literal["daily", "weekly"], diary: str = None, timestamp: float = None, start_date: datetime = None, end_date: datetime = None) -> dict:
        """执行分析（双模式入口）"""
        # 知识检索（不同模式使用不同查询策略）
        knowledge_query = "情绪分析" if mode == "daily" else "长期情绪分析与管理"
        knowledge_retriever = self.knowledge_db.as_retriever(search_kwargs={"k": 5})
        real_knowledge_store = knowledge_retriever.vectorstore
        knowledge_docs = self.safe_retrieve(real_knowledge_store, knowledge_query, 5)
        knowledge_context = "\n".join([d.page_content for d in knowledge_docs]) if knowledge_docs else "暂无专业知识"
        
        if mode == "daily" and diary:
            self.log_diary(diary, timestamp=timestamp)

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
        
    def delete_diary(self, target_datetime: datetime) -> dict:
        """删除指定精确时间的日记（支持到秒）
        Args:
            target_datetime: 包含具体时间的datetime对象
        Returns:
            dict: 操作结果
        """
        
        try:
            
            if not isinstance(target_datetime, datetime):
                raise ValueError("target_datetime 必须是 datetime 类型")
                
            timestamp = int(target_datetime.timestamp())

            
            
            # 验证日记存在
            collection = self.diary_db._collection
            query = {
                "$and": [
                    {"user_id": {"$eq": self.user_id}},
                    {"date": {"$eq": timestamp}}
                ]
            }

            existing = collection.get(where=query)
            ids_to_delete = existing.get('ids', [])
            
            if not ids_to_delete:
                return {
                    "status": "error",
                    "message": "指定时间的日记不存在"
                }
            
            # 使用 ids 执行删除
            result = collection.delete(ids=ids_to_delete)
            # self.diary_db.persist()  # 确保持久化
            
            if result is None or (isinstance(result, dict) and not result.get('ids')):
                # 在这种情况下，我们假设删除已经成功，因为先前已确认了 ids_to_delete 非空
                self.logger.info(f"[SUCCESS] 已删除 {target_datetime} 的日记 (ID: {ids_to_delete})")
                return {
                    "status": "success",
                    "message": "日记删除成功",
                    "deleted_time": target_datetime.isoformat(),
                    "deleted_ids": ids_to_delete  # 添加删除的 ID 信息以便跟踪
                }
            else:
                # 如果 result 中有 ids 信息，使用它们
                deleted_ids = result.get('ids', []) if isinstance(result, dict) else []
                self.logger.info(f"[SUCCESS] 已删除 {target_datetime} 的日记 (ID: {deleted_ids})")
                return {
                    "status": "success",
                    "message": "日记删除成功",
                    "deleted_time": target_datetime.isoformat(),
                    "deleted_ids": deleted_ids
                }
                    
        except Exception as e:
            self.logger.error(f"[ERROR] 删除日记失败: {str(e)}")
            return {
                "status": "error",
                "message": f"删除操作异常: {str(e)}"
            }