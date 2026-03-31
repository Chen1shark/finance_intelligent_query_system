from openai import OpenAI
from src.core.config import get_settings

_client = None


def get_llm_client() -> OpenAI:
    """获取并缓存大模型客户端实例。

    Returns:
        OpenAI: 已按项目配置初始化的 OpenAI 兼容客户端。

    Raises:
        ValueError: 当 ``API_KEY`` 未配置时抛出。
    """
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.api_key:
            raise ValueError("API_KEY 为空，请在 .env 中配置")
        _client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            default_headers=settings.extra_headers,
        )
    return _client
