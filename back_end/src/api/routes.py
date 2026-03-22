from fastapi import APIRouter, HTTPException
from src.core.config import get_settings
from src.core.database import run_query
from src.core.llm_client import get_llm_client
from src.api.schemas import NormalizeRequest
from src.services.crawler_service import CrawlerService
from src.services.semantic_service import SemanticService
from src.services.vector_service import VectorService
from src.services.sql_service import SQLService

settings = get_settings()
router = APIRouter(prefix=settings.api_prefix)


@router.get("/crawl_50etf", summary="抓取并存储50ETF期权数据")
def crawl_50etf_data():
    """
    触发抓取任务：
    1. 调用东方财富接口获取最新50ETF期权数据
    2. 解析并清洗数据
    3. 将数据存入本地MySQL数据库
    """
    try:
        # 1. 抓取数据
        option_data = CrawlerService.fetch_option_data()

        # 2. 写入数据库
        inserted_count = CrawlerService.save_data_to_db(option_data)

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


@router.post("/normalize", summary="规范化50ETF查询文本")
def normalize_text(request: NormalizeRequest):
    """
    使用Qwen3.5-Plus规范化用户输入文本：
    1. 接收用户输入的自然语言文本
    2. 调用Qwen3.5-Plus提取核心信息
    3. 返回规范化后的结果
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="输入文本不能为空")

    try:
        # 调用规范化函数
        result = SemanticService.normalize_50etf_text(request.text)

        if result is None:
            raise HTTPException(status_code=500, detail="模型调用失败，请检查模型配置")

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


@router.post("/extract_core", summary="提取核心需求（纠错后）")
def extract_core(request: NormalizeRequest):
    """
    调用规则匹配并提取"核心需求（纠错后）"的单行文本。
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="输入文本不能为空")
    try:
        result = SemanticService.normalize_50etf_text(request.text)
        if result is None:
            raise HTTPException(status_code=500, detail="模型调用失败，请检查模型配置")
        core_content = SemanticService.extract_core_need_from_text(result)
        core_content = SemanticService.rule_filter_core_need(core_content)
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


@router.post("/match", summary="匹配最相似模板并返回SQL")
def match_template(request: NormalizeRequest):
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="输入文本不能为空")
    try:
        normalized_text = SemanticService.normalize_50etf_text(request.text)
        if normalized_text is None:
            raise HTTPException(status_code=500, detail="模型调用失败，请检查模型配置")
        core_content = SemanticService.extract_core_need_from_text(normalized_text)
        core_content = SemanticService.rule_filter_core_need(core_content)
        results = VectorService.match_user_query(request.text, top_k=1, core_need=core_content)
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


@router.post("/query", summary="生成SQL并查询数据库")
def query_data(request: NormalizeRequest):
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="输入文本不能为空")
    try:
        normalized_text = SemanticService.normalize_50etf_text(request.text)
        if normalized_text is None:
            raise HTTPException(status_code=500, detail="模型调用失败，请检查模型配置")
        core_content = SemanticService.extract_core_need_from_text(normalized_text)
        core_content = SemanticService.rule_filter_core_need(core_content)
        results = VectorService.match_user_query(request.text, top_k=1, core_need=core_content)
        vector_sql = ""
        if results:
            vector_sql = results[0].get("sql") or ""
        sql = SQLService.generate_sql(request.text, normalized_text, vector_sql)
        if not sql:
            raise HTTPException(status_code=500, detail="SQL生成失败")
        data = run_query(sql)
        return {
            "code": 200,
            "msg": "处理成功",
            "data": {
                "normalized_text": normalized_text,
                "core_need": core_content,
                "sql": sql,
                "rows": data,
                "total": len(data)
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query_debug", summary="生成SQL并查询数据库（带性能分析）")
def query_data_debug(request: NormalizeRequest):
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="输入文本不能为空")
    try:
        import time
        
        # 记录开始时间
        start_time = time.time()
        print(f"\n=== 查询流程开始 ===")
        print(f"用户输入: {request.text}")
        print(f"开始时间: {time.strftime('%H:%M:%S', time.localtime(start_time))}")
        
        # 步骤1：语义规范化
        step1_start = time.time()
        normalized_text = SemanticService.normalize_50etf_text(request.text)
        step1_time = time.time() - step1_start
        print(f"\n[步骤1] 语义规范化: {step1_time:.3f}秒")
        
        if normalized_text is None:
            raise HTTPException(status_code=500, detail="模型调用失败，请检查模型配置")
        
        # 步骤2：核心需求提取
        step2_start = time.time()
        core_content = SemanticService.extract_core_need_from_text(normalized_text)
        core_content = SemanticService.rule_filter_core_need(core_content)
        step2_time = time.time() - step2_start
        print(f"[步骤2] 核心需求提取: {step2_time:.3f}秒")
        print(f"核心需求: {core_content}")
        
        # 步骤3：向量检索
        step3_start = time.time()
        results = VectorService.match_user_query(request.text, top_k=1, core_need=core_content)
        step3_time = time.time() - step3_start
        print(f"[步骤3] 向量检索: {step3_time:.3f}秒")
        
        vector_sql = ""
        if results:
            vector_sql = results[0].get("sql") or ""
            print(f"匹配到模板: {results[0].get('question', '')}")
            print(f"相似度: {results[0].get('score', 0):.4f}")
        
        # 步骤4：SQL生成
        step4_start = time.time()
        sql = SQLService.generate_sql(request.text, normalized_text, vector_sql)
        step4_time = time.time() - step4_start
        print(f"[步骤4] SQL生成: {step4_time:.3f}秒")
        print(f"生成SQL: {sql}")
        
        if not sql:
            raise HTTPException(status_code=500, detail="SQL生成失败")
        
        # 步骤5：数据库查询
        step5_start = time.time()
        data = run_query(sql)
        step5_time = time.time() - step5_start
        print(f"[步骤5] 数据库查询: {step5_time:.3f}秒")
        print(f"返回数据: {len(data)}条")
        
        # 总时间统计
        total_time = time.time() - start_time
        print(f"\n=== 流程完成 ===")
        print(f"总耗时: {total_time:.3f}秒")
        print(f"各步骤耗时: 规范化({step1_time:.3f}s) + 提取({step2_time:.3f}s) + 向量({step3_time:.3f}s) + SQL({step4_time:.3f}s) + DB({step5_time:.3f}s)")
        print("=" * 50)
        
        return {
            "code": 200,
            "msg": "处理成功",
            "data": {
                "normalized_text": normalized_text,
                "core_need": core_content,
                "sql": sql,
                "rows": data,
                "total": len(data),
                "performance": {
                    "total_time": round(total_time, 3),
                    "step_times": {
                        "normalization": round(step1_time, 3),
                        "core_extraction": round(step2_time, 3),
                        "vector_search": round(step3_time, 3),
                        "sql_generation": round(step4_time, 3),
                        "database_query": round(step5_time, 3)
                    }
                }
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
