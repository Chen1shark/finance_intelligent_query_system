from pydantic import BaseModel


class NormalizeRequest(BaseModel):
    """规范化请求体结构。"""
    text: str
