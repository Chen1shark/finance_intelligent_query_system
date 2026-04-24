from typing import Any, Dict

from pydantic import BaseModel


class NormalizeRequest(BaseModel):
    """统一的文本查询请求体。

    Attributes:
        text: 用户提交的自然语言查询文本。
    """

    text: str


def api_response(data: Any = None, msg: str = "处理成功", code: int = 200) -> Dict[str, Any]:
    """Build the project's unified API response shape."""
    return {
        "code": code,
        "msg": msg,
        "data": data,
    }
