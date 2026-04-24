from contextlib import asynccontextmanager
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.core.config import get_settings
from src.services.vector_service import VectorService

settings = get_settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """在应用启动阶段预热向量索引资源。

    Args:
        app: 当前 FastAPI 应用实例。

    Yields:
        None: 控制权交还给 FastAPI 继续生命周期流程。
    """
    VectorService.rebuild_vector_store_embeddings()
    yield


app = FastAPI(
    title=settings.project_name,
    description="抓取 50ETF 期权数据并提供自然语言查询接口。",
    version=settings.project_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    logger.info("Starting FastAPI service")
    logger.info("API docs: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
