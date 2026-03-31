from pydantic import BaseModel


class NormalizeRequest(BaseModel):
    """统一的文本查询请求体。

    Attributes:
        text: 用户提交的自然语言查询文本。
    """

    text: str
