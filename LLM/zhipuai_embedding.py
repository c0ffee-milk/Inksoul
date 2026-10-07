from __future__ import annotations
import os
import logging
from typing import Dict, List, Any
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel, Field, model_validator  # 新增Field

logger = logging.getLogger(__name__)

class ZhipuAIEmbeddings(BaseModel, Embeddings):
    """`Zhipuai Embeddings` embedding models."""

    client: Any = None
    zhipuai_api_key: str = Field(..., min_length=32)  # 新增API Key字段

    @model_validator(mode="before")
    @classmethod
    def validate_environment(cls, values: Dict) -> Dict:
        """添加API Key验证和客户端初始化"""
        api_key = (
            values.get("zhipuai_api_key")
            or os.getenv("ZHIPUAI_API_KEY")
            or os.getenv("ZAI_API_KEY")
        )
        
        if not api_key:
            raise ValueError(
                "必须提供ZhipuAI API Key。"
                "可通过以下方式之一设置："
                "1. 构造函数参数 zhipuai_api_key='your_key'"
                "2. 环境变量 ZHIPUAI_API_KEY（或新版 SDK 的 ZAI_API_KEY）"
            )

        values["zhipuai_api_key"] = api_key
        try:
            from zai import ZaiClient
            values["client"] = ZaiClient(api_key=api_key)  # 注入API Key
        except ImportError:
            raise ImportError(
                "无法导入zai模块，请通过 "
                "`pip install zai-sdk` 安装。"
            )
            
        return values

    # 保持原有embed方法不变...
    def embed_query(self, text: str) -> List[float]:
        embeddings = self.client.embeddings.create(
            model="embedding-2",
            input=text
        )
        return embeddings.data[0].embedding
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(text) for text in texts]


