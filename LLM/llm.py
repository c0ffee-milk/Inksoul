# LLM/llm.py
# 日记情绪分析与周报生成。
#
# 调用点只有 routes/auth.py 与 routes/diary.py，它们用到四个接口：
#     analyzer = EmotionAnalyzer("U12")
#     analyzer.log_diary(text=..., timestamp=int)            # 写向量库
#     analyzer.delete_diary(int)                             # 按时间戳删
#     analyzer.analyze("daily", content, int)                # 日报
#     analyzer.analyze(mode="weekly", start_date=..., end_date=...)   # 周报
# 返回值会被 routes 直接塞进 templates/diary_detail.html 与
# templates/weekly_report_detail.html，所以键名和类型必须和模板对得上：
#   daily  : emotion_type / emotion_label(JSON 字符串) / emotional_basis(雷达八维)
#            / keywords(词云 dict) / overall_analysis / history_moment
#            / immediate_suggestion{music{曲名:说明}, books}
#   weekly : diary_review / emotional_basis / domain_event{日期:{event,emotion}}
#            / emotion_trend / weekly_advice / event_key_words / emotion_key_words
#            / famous_quote
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import chromadb
from dotenv import load_dotenv

from LLM.zhipuai_embedding import ZhipuAIEmbeddings

load_dotenv()

logger = logging.getLogger(__name__)

# 目录与模型都可以用环境变量覆盖；默认值对应 .gitignore 里已经预留的路径
DIARY_DB_DIR = os.getenv("DIARY_DB_DIR", "data_base/diary_db")
KNOWLEDGE_DB_DIR = os.getenv("KNOWLEDGE_DB_DIR", "data_base/knowledge_db")
KNOWLEDGE_COLLECTION = os.getenv("KNOWLEDGE_COLLECTION", "langchain")
CHAT_MODEL = os.getenv("ZAI_CHAT_MODEL", "glm-4-flash")

# 六类情绪，index.html 的情绪搜索按钮用的就是这六个
EMOTION_TYPES = ["振奋", "愉悦", "平和", "焦虑", "低落", "烦闷"]
# 雷达图八维，对应 static/js/analysis.js 里的 newOrder
RADAR_EMOTIONS = ["喜悦", "期待", "信任", "惊讶", "生气", "厌恶", "难过", "害怕"]

DAILY_SYSTEM_PROMPT = """你是一位兼具心理学素养与文学修养的日记分析助手。
你需要阅读用户的日记，输出一份中文 JSON 分析报告，且只输出 JSON，不要输出任何解释或代码块标记。

JSON 字段要求：
- emotion_type: 字符串，必须从这六个里选一个最贴切的：{emotion_types}
- emotion_label: 字符串数组，1~4 个情绪词，按主次排序，用来描述情绪流动
- emotional_basis: 对象，键必须是 {radar_emotions}，值为 0~100 的整数，表示该情绪在日记中的强度（没有体现的维度给 0）
- keywords: 对象，5~15 个词，键是日记里的关键词（2~6 字），值是 0~100 的权重
- overall_analysis: 字符串，200 字以内的综合分析，第二人称、温和具体
- history_moment: 字符串，150 字以内，围绕日记里的处境给一段历史掌故或名人经历作对照
- immediate_suggestion: 对象，含两个字段：
    - music: 对象，1~3 项，键是曲名，值是一句话说明为什么推荐
    - books: 字符串，1~2 本书的书名加一句话推荐理由
""".format(emotion_types="、".join(EMOTION_TYPES), radar_emotions="、".join(RADAR_EMOTIONS))

WEEKLY_SYSTEM_PROMPT = """你是一位兼具心理学素养与文学修养的周记分析助手。
你需要阅读用户一周内的全部日记，输出一份中文 JSON 周报，且只输出 JSON，不要输出任何解释或代码块标记。

JSON 字段要求：
- diary_review: 字符串，200 字以内的一周回顾，第二人称
- emotional_basis: 对象，键是情绪类别（从 {emotion_types} 里选 2~6 个），值为该情绪在本周占比（0~100 的整数）
- domain_event: 对象，键是日期（格式 YYYY-MM-DD），值是对象 {{"event": "当天主导事件", "emotion": "当天主导情绪"}}
- emotion_trend: 字符串，150 字以内的情绪变化趋势分析
- weekly_advice: 字符串，150 字以内的一周长期建议
- event_key_words: 对象，5~15 个事件关键词，值是 0~100 的权重
- emotion_key_words: 对象，5~15 个情绪关键词，值是 0~100 的权重
- famous_quote: 字符串，一句贴合本周心境的名言，附出处
""".format(emotion_types="、".join(EMOTION_TYPES))


class EmotionAnalyzer:
    """按用户维度读写日记向量库，并调用大模型产出日报/周报。"""

    def __init__(self, user_id: str):
        user_id = str(user_id or "").strip()
        if not user_id.startswith("U"):
            # 调用手册与所有调用点都约定 user_id 形如 "U12"
            raise ValueError(f"user_id 必须以 U 开头，收到：{user_id!r}")
        self.user_id = user_id
        self._chat_client_obj = None
        self._embedding_obj = None
        self._diary_collection_obj = None
        self._knowledge_collection_obj = None

    # ------------------------------------------------------------------ 资源
    @property
    def api_key(self) -> str:
        key = os.getenv("ZHIPUAI_API_KEY") or os.getenv("ZAI_API_KEY")
        if not key:
            raise RuntimeError(
                "未配置 API Key：请设置环境变量 ZHIPUAI_API_KEY（或新 SDK 的 ZAI_API_KEY）"
            )
        return key

    @property
    def embedding(self) -> ZhipuAIEmbeddings:
        if self._embedding_obj is None:
            self._embedding_obj = ZhipuAIEmbeddings(zhipuai_api_key=self.api_key)
        return self._embedding_obj

    @property
    def chat_client(self):
        if self._chat_client_obj is None:
            from zai import ZaiClient

            self._chat_client_obj = ZaiClient(api_key=self.api_key)
        return self._chat_client_obj

    @property
    def collection(self):
        if self._diary_collection_obj is None:
            safe_id = re.sub(r"[^a-zA-Z0-9._-]", "_", self.user_id)
            client = chromadb.PersistentClient(path=DIARY_DB_DIR)
            self._diary_collection_obj = client.get_or_create_collection(
                name=f"diary_{safe_id}"
            )
        return self._diary_collection_obj

    # -------------------------------------------------------------- 向量库读写
    @staticmethod
    def _to_timestamp(value: Union[int, float, datetime, None]) -> int:
        if value is None:
            return int(datetime.now().timestamp())
        if isinstance(value, datetime):
            return int(value.timestamp())
        if isinstance(value, (int, float)):
            return int(value)
        # 兼容调用手册里写的字符串时间
        return int(datetime.fromisoformat(str(value)).timestamp())

    @staticmethod
    def _entry_id(user_id: str, timestamp: int) -> str:
        return f"{user_id}-{timestamp}"

    def log_diary(self, text: str, timestamp: Union[int, float, datetime, None] = None) -> Dict[str, Any]:
        """把一篇日记写进该用户的向量库（同一时间戳重复写入会覆盖）。"""
        if not text or not str(text).strip():
            raise ValueError("日记内容不能为空")
        ts = self._to_timestamp(timestamp)
        self.collection.upsert(
            ids=[self._entry_id(self.user_id, ts)],
            documents=[str(text)],
            embeddings=[self.embedding.embed_query(str(text))],
            metadatas=[{"timestamp": ts, "datetime": datetime.fromtimestamp(ts).isoformat(timespec="seconds")}],
        )
        return {"success": True, "timestamp": ts, "count": self.collection.count()}

    def delete_diary(self, timestamp: Union[int, float, datetime, None] = None) -> Dict[str, Any]:
        """按时间戳删除向量库里的日记。没有匹配项时返回 deleted=0，不抛异常。"""
        ts = self._to_timestamp(timestamp)
        before = self.collection.count()
        self.collection.delete(where={"timestamp": {"$eq": ts}})
        after = self.collection.count()
        return {"success": True, "timestamp": ts, "deleted": before - after}

    def _entries_between(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        data = self.collection.get(
            where={"$and": [
                {"timestamp": {"$gte": int(start.timestamp())}},
                {"timestamp": {"$lte": int(end.timestamp())}},
            ]},
            include=["documents", "metadatas"],
        )
        entries = []
        for doc, meta in zip(data.get("documents") or [], data.get("metadatas") or []):
            ts = int((meta or {}).get("timestamp", 0))
            entries.append({
                "timestamp": ts,
                "datetime": datetime.fromtimestamp(ts),
                "text": doc or "",
            })
        return sorted(entries, key=lambda e: e["timestamp"])

    def _knowledge_context(self, query: str, k: int = 3) -> str:
        """从心理学知识库取参考段落。知识库不存在或没建索引时静默跳过。"""
        try:
            if self._knowledge_collection_obj is None:
                client = chromadb.PersistentClient(path=KNOWLEDGE_DB_DIR)
                self._knowledge_collection_obj = client.get_collection(KNOWLEDGE_COLLECTION)
            if self._knowledge_collection_obj.count() == 0:
                return ""
            result = self._knowledge_collection_obj.query(
                query_embeddings=[self.embedding.embed_query(query)], n_results=k
            )
            docs = [d for d in (result.get("documents") or [[]])[0] if d]
            return "\n\n".join(docs)
        except Exception as exc:  # 知识库是可选增强，失败不影响分析
            logger.warning("知识库检索跳过：%s", exc)
            return ""

    # ------------------------------------------------------------------ 大模型
    def _chat_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        response = self.chat_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return self._parse_json(content)

    @staticmethod
    def _parse_json(content: str) -> Dict[str, Any]:
        text = content.strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.S)
            if not match:
                raise ValueError(f"模型没有返回 JSON：{content[:200]}")
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                raise ValueError(f"模型返回的 JSON 无法解析：{content[:200]}")
        if not isinstance(data, dict):
            raise ValueError(f"模型返回的 JSON 不是对象：{content[:200]}")
        return data

    # ------------------------------------------------------------------ 规范化
    @staticmethod
    def _as_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _as_number(value: Any) -> float:
        if isinstance(value, bool):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"-?\d+(?:\.\d+)?", value)
            if match:
                return float(match.group(0))
        return 0.0

    @classmethod
    def _as_weight_map(cls, value: Any, limit: int = 20) -> Dict[str, float]:
        """词云数据：模板和 JS 都按 {词: 权重} 消费，这里把各种模型输出统一成这个形状。"""
        result: Dict[str, float] = {}
        if isinstance(value, dict):
            items = value.items()
        elif isinstance(value, list):
            items = []
            for item in value:
                if isinstance(item, dict):
                    word = item.get("word") or item.get("keyword") or item.get("name") or item.get("text")
                    weight = item.get("weight") or item.get("value") or item.get("score") or 50
                    items.append((word, weight))
                elif isinstance(item, str):
                    items.append((item, 50))
        else:
            items = []
        for word, weight in items:
            word = cls._as_text(word)
            if word:
                result[word] = cls._as_number(weight)
        return dict(list(result.items())[:limit])

    @classmethod
    def _as_json_string_list(cls, value: Any) -> str:
        """模板用 |fromjson 解析 emotion_label，所以这里必须返回 JSON 字符串。"""
        if isinstance(value, str):
            stripped = value.strip()
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = [p for p in re.split(r"[、,，/\s]+", stripped) if p]
        elif isinstance(value, (list, tuple)):
            parsed = list(value)
        else:
            parsed = []
        cleaned = [cls._as_text(v) for v in parsed if cls._as_text(v)]
        return json.dumps(cleaned, ensure_ascii=False)

    @classmethod
    def _radar_basis(cls, value: Any) -> Dict[str, int]:
        raw = cls._as_weight_map(value, limit=len(RADAR_EMOTIONS) + 8)
        basis = {}
        for emotion in RADAR_EMOTIONS:
            number = cls._as_number(raw.get(emotion, 0))
            basis[emotion] = max(0, min(100, int(round(number))))
        return basis

    @classmethod
    def _daily_result(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        emotion_type = cls._as_text(data.get("emotion_type"))
        if emotion_type not in EMOTION_TYPES:
            emotion_type = EMOTION_TYPES[2]  # 无法归类时落到“平和”
        suggestion = data.get("immediate_suggestion") or {}
        if not isinstance(suggestion, dict):
            suggestion = {}
        music = suggestion.get("music") or {}
        if isinstance(music, list):
            music = {cls._as_text(m.get("name") if isinstance(m, dict) else m):
                     cls._as_text(m.get("reason")) if isinstance(m, dict) else ""
                     for m in music}
        elif not isinstance(music, dict):
            music = {}
        return {
            "emotion_type": emotion_type,
            "emotion_label": cls._as_json_string_list(data.get("emotion_label")),
            "emotional_basis": cls._radar_basis(data.get("emotional_basis")),
            "keywords": cls._as_weight_map(data.get("keywords")),
            "overall_analysis": cls._as_text(data.get("overall_analysis")),
            "history_moment": cls._as_text(data.get("history_moment")),
            "immediate_suggestion": {
                "music": {cls._as_text(k): cls._as_text(v) for k, v in music.items()},
                "books": cls._as_text(suggestion.get("books")),
            },
        }

    @classmethod
    def _weekly_result(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        domain_event = {}
        raw_events = data.get("domain_event") or {}
        if isinstance(raw_events, dict):
            for day, value in raw_events.items():
                if isinstance(value, dict):
                    domain_event[cls._as_text(day)] = {
                        "event": cls._as_text(value.get("event")),
                        "emotion": cls._as_text(value.get("emotion")),
                    }
                else:
                    domain_event[cls._as_text(day)] = {"event": cls._as_text(value), "emotion": ""}
        return {
            "diary_review": cls._as_text(data.get("diary_review")),
            "emotional_basis": cls._as_weight_map(data.get("emotional_basis")),
            "domain_event": domain_event,
            "emotion_trend": cls._as_text(data.get("emotion_trend")),
            "weekly_advice": cls._as_text(data.get("weekly_advice")),
            "event_key_words": cls._as_weight_map(data.get("event_key_words")),
            "emotion_key_words": cls._as_weight_map(data.get("emotion_key_words")),
            "famous_quote": cls._as_text(data.get("famous_quote")),
        }

    # -------------------------------------------------------------------- 分析
    def analyze(
        self,
        mode: str = "daily",
        diary: Optional[str] = None,
        timestamp: Union[int, float, datetime, None] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        mode = (mode or "daily").strip().lower()
        if mode == "daily":
            return self._analyze_daily(diary, timestamp)
        if mode == "weekly":
            return self._analyze_weekly(start_date, end_date)
        raise ValueError(f"未知的分析模式：{mode!r}（只支持 daily / weekly）")

    def _analyze_daily(self, diary: Optional[str], timestamp) -> Dict[str, Any]:
        if not diary or not str(diary).strip():
            raise ValueError("daily 模式必须提供日记内容")
        ts = self._to_timestamp(timestamp)

        parts = [f"【日记】\n{diary}"]
        context = self._knowledge_context(str(diary))
        if context:
            parts.append(f"【心理学参考资料（仅供理解，不要照抄）】\n{context}")
        try:
            recent = self._entries_between(datetime.fromtimestamp(0), datetime.fromtimestamp(ts - 1))[-5:]
        except Exception as exc:
            logger.warning("读取历史日记失败：%s", exc)
            recent = []
        if recent:
            history = "\n".join(f"[{e['datetime']:%Y-%m-%d}] {e['text'][:120]}" for e in recent)
            parts.append(f"【该用户更早的日记（可作对照，不要复述）】\n{history}")
        parts.append(f"今天是 {datetime.fromtimestamp(ts):%Y-%m-%d}，请按要求输出 JSON。")

        data = self._chat_json(DAILY_SYSTEM_PROMPT, "\n\n".join(parts))
        return self._daily_result(data)

    def _analyze_weekly(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> Dict[str, Any]:
        end = end_date or datetime.now()
        start = start_date or (end - timedelta(days=6))
        if not isinstance(start, datetime):
            start = datetime.combine(start, datetime.min.time())
        if not isinstance(end, datetime):
            end = datetime.combine(end, datetime.max.time())

        entries = self._entries_between(start, end)
        if not entries:
            raise ValueError("该时间段内没有日记记录")
        diaries = "\n\n".join(
            f"[{e['datetime']:%Y-%m-%d}] {e['text']}" for e in entries
        )
        user_prompt = (
            f"【统计区间】{start:%Y-%m-%d} 至 {end:%Y-%m-%d}（共 {len(entries)} 篇日记）\n\n"
            f"【日记原文】\n{diaries}\n\n请按要求输出 JSON 周报。"
        )
        data = self._chat_json(WEEKLY_SYSTEM_PROMPT, user_prompt)
        return self._weekly_result(data)
