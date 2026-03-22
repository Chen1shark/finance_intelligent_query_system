from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field

# 项目根目录（.env 所在位置）
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    """应用配置，从 .env 文件加载"""

    # LLM API 配置
    api_key: str = Field(default="", alias="API_KEY")
    base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1", alias="BASE_URL")
    model_name: str = Field(default="qwen3.5-flash", alias="MODEL_NAME")
    embed_model: str = Field(default="text-embedding-v4", alias="EMBED_MODEL")
    temperature: float = Field(default=0.0, alias="TEMPERATURE")
    thinking_enable: bool = Field(
        default=False,
        validation_alias=AliasChoices("THINKING_ENABLE", "THINKIN_ENABLE"),
    )

    # 数据库配置
    db_host: str = Field(default="127.0.0.1", alias="DB_HOST")
    db_port: int = Field(default=3306, alias="DB_PORT")
    db_user: str = Field(default="root", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_name: str = Field(default="eastmoney_db", alias="DB_NAME")

    # 爬虫配置
    target_url: str = Field(
        default="http://push2.eastmoney.com/api/qt/clist/get",
        alias="TARGET_URL"
    )

    # 项目配置
    project_name: str = Field(default="50ETF期权智能问数系统", alias="PROJECT_NAME")
    project_version: str = Field(default="1.0.0", alias="PROJECT_VERSION")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")

    # Extra headers（硬编码，不需要从 .env 加载）
    extra_headers: dict = {"Content-Type": "application/json; charset=utf-8"}

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
