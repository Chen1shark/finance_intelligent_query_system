from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    """Application settings loaded from the project .env file."""

    api_key: str = Field(default="", alias="API_KEY")
    base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1", alias="BASE_URL")
    model_name: str = Field(default="qwen3.5-flash", alias="MODEL_NAME")
    embed_model: str = Field(default="text-embedding-v4", alias="EMBED_MODEL")
    temperature: float = Field(default=0.0, alias="TEMPERATURE")
    thinking_enable: bool = Field(
        default=False,
        validation_alias=AliasChoices("THINKING_ENABLE", "THINKIN_ENABLE"),
    )

    db_host: str = Field(default="127.0.0.1", alias="DB_HOST")
    db_port: int = Field(default=3306, alias="DB_PORT")
    db_user: str = Field(default="root", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_name: str = Field(default="eastmoney_db", alias="DB_NAME")

    target_url: str = Field(default="http://push2.eastmoney.com/api/qt/clist/get", alias="TARGET_URL")

    project_name: str = Field(default="50ETF期权智能问数系统", alias="PROJECT_NAME")
    project_version: str = Field(default="1.0.0", alias="PROJECT_VERSION")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")

    extra_headers: dict = {"Content-Type": "application/json; charset=utf-8"}

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """获取全局缓存的应用配置对象。

    Returns:
        Settings: 从环境变量和 ``.env`` 文件解析得到的配置实例。
    """
    return Settings()
