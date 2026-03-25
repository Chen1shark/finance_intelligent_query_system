from pydantic import BaseModel


class NormalizeRequest(BaseModel):
    """统一的文本查询请求体。"""

    text: str
