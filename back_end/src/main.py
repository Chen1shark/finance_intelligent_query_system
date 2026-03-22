# ==============================================================================
# 服务运行入口
# ==============================================================================
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from src.core.config import get_settings
from src.api.routes import router
from src.services.vector_service import VectorService

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    VectorService.rebuild_vector_store_embeddings()
    yield
    # shutdown


# 创建FastAPI应用
app = FastAPI(
    title=settings.project_name,
    description="从东方财富抓取50ETF期权数据并写入MySQL数据库",
    version=settings.project_version,
    lifespan=lifespan,
)

# 注册API路由
app.include_router(router)

if __name__ == "__main__":
    print("启动FastAPI服务...")
    print("接口文档地址: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
