# ==============================================================================
# 服务运行入口
# ==============================================================================
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import config
from crawler import fetch_option_data, save_data_to_db
from normalize_50etf import normalize_50etf_text, extract_core_need_from_text, rule_filter_core_need
from faiss_matcher import rebuild_vector_store_embeddings, match_user_query

# 创建FastAPI应用
app = FastAPI(
    title=config.PROJECT_NAME,
    description="从东方财富抓取50ETF期权数据并写入MySQL数据库",
    version=config.PROJECT_VERSION
)

@app.on_event("startup")
def rebuild_embeddings_on_startup():
    rebuild_vector_store_embeddings()

# 请求模型
class NormalizeRequest(BaseModel):
    """规范化请求体结构。"""
    text: str

# 注册API路由
@app.get(f"{config.API_PREFIX}/crawl_50etf", summary="抓取并存储50ETF期权数据")
def crawl_50etf_data():
    """
    触发抓取任务：
    1. 调用东方财富接口获取最新50ETF期权数据
    2. 解析并清洗数据
    3. 将数据存入本地MySQL数据库
    """
    try:
        # 1. 抓取数据
        option_data = fetch_option_data()
        
        # 2. 写入数据库
        inserted_count = save_data_to_db(option_data)
        
        # 3. 返回结果
        return {
            "code": 200,
            "msg": "数据入库成功",
            "data": {
                "total": inserted_count
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"{config.API_PREFIX}/normalize", summary="规范化50ETF查询文本")
def normalize_text(request: NormalizeRequest):
    """
    使用本地Ollama模型规范化用户输入文本：
    1. 接收用户输入的自然语言文本
    2. 调用qwen7b模型提取50ETF核心信息
    3. 返回规范化后的结果
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="输入文本不能为空")
        
    try:
        # 调用规范化函数
        result = normalize_50etf_text(request.text)
        
        if result is None:
            raise HTTPException(status_code=500, detail="模型调用失败，请检查Ollama服务状态")
            
        return {
            "code": 200,
            "msg": "处理成功",
            "data": {
                "original_text": request.text,
                "normalized_text": result
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"{config.API_PREFIX}/extract_core", summary="提取核心需求（纠错后）")
def extract_core(request: NormalizeRequest):
    """
    调用规则匹配并提取“核心需求（纠错后）”的单行文本。
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="输入文本不能为空")
    try:
        result = normalize_50etf_text(request.text)
        if result is None:
            raise HTTPException(status_code=500, detail="模型调用失败，请检查Ollama服务状态")
        core_content = extract_core_need_from_text(result)
        core_content = rule_filter_core_need(core_content)
        return {
            "code": 200,
            "msg": "处理成功",
            "data": {
                "original_text": request.text,
                "core_need": core_content
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"{config.API_PREFIX}/match", summary="匹配最相似模板并返回SQL")
def match_template(request: NormalizeRequest):
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="输入文本不能为空")
    try:
        normalized_text = normalize_50etf_text(request.text)
        if normalized_text is None:
            raise HTTPException(status_code=500, detail="模型调用失败，请检查Ollama服务状态")
        core_content = extract_core_need_from_text(normalized_text)
        core_content = rule_filter_core_need(core_content)
        results = match_user_query(request.text, top_k=1, core_need=core_content)
        if not results:
            raise HTTPException(status_code=404, detail="未匹配到模板")
        best = results[0]
        return {
            "code": 200,
            "msg": "处理成功",
            "data": {
                "normalized_text": normalized_text,
                "core_need": best.get("core_need"),
                "score": best.get("score"),
                "question": best.get("question"),
                "sql": best.get("sql")
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("启动FastAPI服务...")
    print("接口文档地址: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
