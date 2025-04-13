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


# 加载环境变量配置
load_dotenv()  # 加载.env文件
os.environ["LANGCHAIN_DISABLE_PYDANTIC_WARNINGS"] = "1"

# API密钥配置
ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY")  # 智谱AI API密钥
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # DeepSeek API密钥
TONGYI_API_KEY = os.getenv("TONGYI_API_KEY")  # 通义API密钥

# ================== 增强型数据库管理器 ==================
class VectorDBManager:
    """
    向量数据库管理器
    负责管理知识库和用户日记库的存储、检索和删除操作
    使用Chroma向量数据库实现文本的向量化存储和检索
    """
    def __init__(self):
        """
        初始化向量数据库管理器
        设置嵌入模型和日志记录器
        """
        self.embedding = ZhipuAIEmbeddings(zhipuai_api_key=ZHIPUAI_API_KEY)
        self.logger = logging.getLogger("VectorDBManager")
        self.logger.addHandler(logging.NullHandler())
        
    def get_knowledge_db(self) -> Chroma:
        """
        获取心理学知识库
        用于存储和检索心理学相关的知识内容
        
        Returns:
            Chroma: 知识库实例
        """
        return Chroma(
            persist_directory='data_base/knowledge_db',
            embedding_function=self.embedding,
            collection_name="knowledge"
        )
    
    def get_diary_db(self, user_id: str) -> Chroma:
        """
        获取用户日记库
        为每个用户创建独立的日记存储空间
        
        Args:
            user_id (str): 用户ID，格式为"U"开头加数字
            
        Returns:
            Chroma: 用户专属的日记库实例
            
        Raises:
            PermissionError: 当目录无写入权限时抛出
        """
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
        """
        根据精确时间戳删除日记
        
        Args:
            user_id (str): 用户ID
            timestamp (float): 精确到秒的时间戳
            
        Returns:
            bool: 删除是否成功
            
        Note:
            使用精确匹配确保只删除指定时间的日记
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
    """
    情感分析引擎
    基于大语言模型和心理学理论，对用户日记进行深度情感分析
    支持日常分析和周期性分析两种模式
    """
    def __init__(self, user_id: str):
        """
        初始化情感分析引擎
        
        Args:
            user_id (str): 用户ID，格式为"U"开头加数字
            
        Raises:
            ValueError: 当用户ID格式不正确时抛出
        """
        self.user_id = user_id
        
        # 验证用户ID格式
        if not re.match(r"^U\d+$", self.user_id):
            raise ValueError("用户ID格式应为 U+数字")
        
        # 配置日志记录器
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
        
        # 初始化数据库和语言模型
        self.db = VectorDBManager()
        self.llm = ChatOpenAI(
            temperature=0,
            openai_api_key=DEEPSEEK_API_KEY,
            model_name="deepseek-chat",
            base_url="https://api.deepseek.com"
        )
        
        # 初始化数据库连接
        self.knowledge_db = self.db.get_knowledge_db()
        self.diary_db = self.db.get_diary_db(self.user_id)

        # 验证数据库目录
        assert os.path.exists(self.diary_db._persist_directory), "用户数据库目录未创建"
        
        # 初始化提示模板
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
                3. 根据这几种基本情感的含量与组合效果和原文本细致分析出几个复合情绪的种类：emotion_lable（复杂情绪）
                4. 根据用户日记体现的情绪，将本日记分为以下六种中的一种(振奋、愉悦、平和、焦虑、低落、烦闷)：emotion_type（情绪类型）
                5. 在原文中提取当日事件的关键词及其关键程度：keywords（5个以上个关键词）
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
                        "情绪1",
                        "情绪2",
                        ...
                    ],
                    "emotion_type": "情绪类型",
                    "keywords": {{
                        "关键词1": 0-100,
                        "关键词2": 0-100, 
                        "关键词3": 0-100,
                        ...
                    }},
                    "immediate_suggestion": {{
                        "music":{{
                            "music_suggestion1":"音乐推荐与推荐理由1",
                            "music_suggestion2":"音乐推荐与推荐理由2"
                        }}, 
                        "books":"书籍推荐与推荐理由",
                        "activities":"活动建议",
                        "techniques":"心理调节技巧"
                    }},
                    "history_moment": "历史回响内容"
                }}

                输出示例：
                {{'overall_analysis': '您的日记展现了一种细腻的生活观察与复杂的情感交织。晨跑时的太极老人、早餐铺的温暖互动、旧书店的怀旧时光，都透露出对生活细节的敏感捕捉。然而，升舱短信触发的记忆、帮邻居修门锁时的代际差异，以及电梯里的疲惫面孔，又暗示着某种对时间流逝和现代生活疏离感的微妙焦虑。整体上，您的情感基调是平和中有波澜，温暖里带沉思。', 'emotional_basis': {{'喜悦': 65, '信任': 70, '害怕': 20, '惊讶': 30, '难过': 40, '厌恶': 10, '生气': 5, '期待': 50}}, 'emotion_label': ['怀旧的慰藉', '温柔的疏离', '时光焦虑'], 'emotion_type': '平和', 'keywords': {{'晨跑太极': 85, '早餐铺人情': 90, '旧书店怀旧': 75, '里程过期': 60, '赛博弄堂': 50, '电梯疲惫': 40}}, 'immediate_suggestion': {{'music': {{'music_suggestion1': '《Rainy Day》- Coldplay，舒缓的旋律适合雨天放松心情', 'music_suggestion2': '《A Thousand Years》- Christina Perri，温柔的节奏帮助您平静思考'}}, 'books': '《看不见的城市》- 卡尔维诺，关于记忆与城市的诗意叙述，与您发现的粮票形成互文', 'activities': '今晚适合用老式信纸给三年后的自己写封信，定格此刻对时间流逝的感悟', 'techniques': '明早买早餐时专注记录三种声音、两种质地，用感官体验对抗抽象焦虑'}}, 'history_moment': '1935年，本雅明在巴黎旧书摊淘到一张19世纪明信片时同样怔住——那些被遗忘的通讯地址，与您发现的粮票一样，都是时光洪流中的漂流瓶。'}}
                """
            ),
            "weekly": PromptTemplate(
                input_variables=["knowledge", "diaries"],
                template="""您是情绪分析专家，基于Robert Plutchik情感轮盘理论和当代复合情绪研究模型，对过去一段时间的日记进行周期性分析：
                
                【心理学理论】
                {knowledge}
                
                【日记记录】
                {diaries}
                
                请输出JSON包含：
                1. 以第二人称讲述的形式回顾用户过去这段时间的经历：diary_review
                2. 喜悦、信任、害怕、惊讶、难过、厌恶、生气、期待这八种基本感情的组成含量（0-100%）:emotional_basis(情感构成）
                3. 提取这段时间内有日记记录的每天的一个主要事件（每篇日记的第一行为撰写日期，若一天有多篇日记则合并进行分析，不管一天有多少篇日记均只输出一个主导事件，按时间排序输出）：domain_event(主要事件)，
                4. 分析这段时间的情绪变化趋势：emotion_trend（情绪变化趋势描述）
                5. 针对这段时间的情绪提出给用户下一周的建议：weekly_advice（长期建议）
                6. 总结这段时间的主导事件找出5-10个事件关键词及其关键程度：event_key_words
                7. 总结这段时间的主导情绪找出5-10个情绪关键词及其关键程度：emotion_key_words
                8. 结合用户这段时间的心理情绪找一段名人或名著的名言，作为总结的引言：famous_quote

                输出要求：
                1.面向用户输出，注意人称用词必须用您
                2.提出的建议要基于现实，容易实现

                输出格式：
                {{
                    "diary_review": "日记回顾",
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
                    "domain_event": {{
                        "day1": {{"event": "事件1", "emotion": "情绪1"}},
                        "day2": {{"event": "事件2", "emotion": "情绪2"}},
                        ......((每天只总结一个事件))
                    }},
                    "emotion_trend": "情绪变化趋势",
                    "weekly_advice": "本周长期建议（一段话）",
                    "event_key_words": {{
                        "关键词1": 0-100,
                        "关键词2": 0-100, 
                        "关键词3": 0-100,
                        ......
                    }},
                    "emotion_key_words": {{
                        "关键词1": 0-100,
                        "关键词2": 0-100, 
                        "关键词3": 0-100,
                        ......
                    }},
                    "famous_quote": "名言引文"
                }}

                输出示例：
                {{'diary_review': '过去几天里，您的生活充满了细腻的观察和微妙的情感波动。从雨中回忆童年，到与同事共享辣味午餐；从清晨被桂花香唤醒，到深夜弹奏生锈的吉他；从发现社区图书馆的温暖，到与发小跨越时空的对话——这些片段交织成您独特的情感图谱。您既在日常生活里捕捉诗意（如羊角包香气与钢琴声的交融），也在科技与传统的碰撞中思考（如元宇宙作业与石库门青苔的对比）。', 'emotional_basis': {{'喜悦': 35, '信任': 25, '害怕': 10, '惊讶': 20, '难过': 30, '厌恶': 5, '生气': 5, '期待': 40}}, 'domain_event': {{'2024-6-15': {{'event': '被桂花香唤醒并完成重要提案', 'emotion': '欣慰与成就感'}}, '2024-6-16': {{'event': '雨中回忆童年并与同事共进辣味午餐', 'emotion': '怀旧与温暖'}}, '2024-6-17': {{'event': '与发小跨时空对话并发现社区图书馆夜读区', 'emotion': '连接感与宁静'}}, '2024-6-18': {{'event': '发现旧书店粮票与收到里程过期提醒', 'emotion': '时光流逝的怅惘'}}}}, 'emotion_trend': '情绪呈现波浪式变化，从15日的积极满足，到16日加入怀旧色彩，17日达到情感连接的高点，18日因时间感知而产生轻微低落。期待感始终作为基底情绪存在，但后期混合了更多对时光流逝的敏感。', 'weekly_advice': "建议每天预留15分钟'感官时刻'：周一闻三种不同气味，周二触摸五种材质，周三记录三种声音，周四观察光线变化，周五重温旧物触感。周末可尝试将吉他送去换弦，或拜访那位读普鲁斯特的猫店主。这些微型仪式能锚定您对当下的感知，缓解时间焦虑。", 'event_key_words': {{'怀旧触发': 70, '跨代交流': 60, '感官记忆': 85, '时间感知': 75, '科技与传统碰撞': 50, '微小确幸': 65, '未完成计划': 40, '城市诗意': 55}}, 'emotion_key_words': {{'温柔的怅惘': 60, '克制的喜悦': 45, '悬浮的期待': 70, '疏离的观察': 35, '时光焦虑': 50, '连接渴望': 55, '审美触动': 65, '幽默化解': 30}}, 'famous_quote': '「记忆中的形象一旦被词语固定住，就会抹去其他可能的含义。」——卡尔维诺《看不见的城市》'}}
                """
            )
        }

    def _get_time_range(self, start: datetime = None, end: datetime = None, days: int = 7) -> dict:
        """
        生成时间范围查询条件
        
        Args:
            start (datetime, optional): 开始时间
            end (datetime, optional): 结束时间
            days (int, optional): 天数，默认7天
            
        Returns:
            dict: MongoDB查询条件
        """
        end = end or datetime.now()
        start = start or (end - timedelta(days=days))
        return {
            "$and": [
                {"date": {"$gte": int(start.timestamp())}},
                {"date": {"$lte": int(end.timestamp())}}
            ]
        }

    def safe_retrieve(self, collection, query: str, k: int, filter_: dict = None) -> list:
        """
        安全的向量检索方法
        
        Args:
            collection: 向量数据库集合
            query (str): 查询文本
            k (int): 返回结果数量
            filter_ (dict, optional): 过滤条件
            
        Returns:
            list: 检索结果列表
            
        Note:
            包含错误处理和结果数量调整
        """
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
        """
        检索用户日记
        
        Args:
            mode (Literal["daily", "weekly"]): 检索模式
            query (str, optional): 查询文本
            start (datetime, optional): 开始时间
            end (datetime, optional): 结束时间
            days (int, optional): 天数
            
        Returns:
            str: 合并后的日记文本
        """
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
        """
        保存日记到向量数据库
        
        Args:
            text (str): 日记内容
            timestamp (float, optional): 时间戳，精确到秒
            
        Note:
            会检查重复日记，避免重复保存
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
            self.logger.info(f"[SUCCESS] 日记已保存（时间：{datetime.fromtimestamp(timestamp)}）")
        except Exception as e:
            self.logger.error(f"[ERROR] 保存失败: {str(e)}")
            raise

    def get_diary_dates(self) -> list:
        """
        获取用户所有日记的日期列表
        
        Returns:
            list: 按时间排序的日期列表
            
        Note:
            返回的日期格式为 "YYYY-MM-DD"
        """
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
        """
        执行情感分析
        
        Args:
            mode (Literal["daily", "weekly"]): 分析模式
            diary (str, optional): 日记内容（日常模式需要）
            timestamp (float, optional): 时间戳
            start_date (datetime, optional): 开始日期（周期模式需要）
            end_date (datetime, optional): 结束日期（周期模式需要）
            
        Returns:
            dict: 分析结果
            
        Note:
            支持日常分析和周期分析两种模式
        """
        # 知识检索（不同模式使用不同查询策略）
        knowledge_query = "情绪分析" if mode == "daily" else "长期情绪分析与管理"
        knowledge_retriever = self.knowledge_db.as_retriever(search_kwargs={"k": 5})
        real_knowledge_store = knowledge_retriever.vectorstore
        knowledge_docs = self.safe_retrieve(real_knowledge_store, knowledge_query, 5)
        knowledge_context = "\n".join([d.page_content for d in knowledge_docs]) if knowledge_docs else "暂无专业知识"

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
        """
        删除指定时间的日记
        
        Args:
            target_datetime (datetime): 目标时间
            
        Returns:
            dict: 操作结果
            
        Note:
            支持精确到秒的删除操作
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
            
            result = collection.delete(ids=ids_to_delete)
            
            if result is None or (isinstance(result, dict) and not result.get('ids')):
                self.logger.info(f"[SUCCESS] 已删除 {target_datetime} 的日记 (ID: {ids_to_delete})")
                return {
                    "status": "success",
                    "message": "日记删除成功",
                    "deleted_time": target_datetime.isoformat(),
                    "deleted_ids": ids_to_delete
                }
            else:
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