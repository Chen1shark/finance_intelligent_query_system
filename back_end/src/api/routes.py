import logging
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException

from src.api.schemas import NormalizeRequest
from src.core.config import get_settings
from src.core.database import run_query
from src.services.crawler_service import CrawlerService
from src.services.semantic_service import SemanticService
from src.services.sql_service import SQLService
from src.services.vector_service import VectorService

settings = get_settings()
router = APIRouter(prefix=settings.api_prefix)
logger = logging.getLogger(__name__)

CRAWL_FAILURE_MESSAGE = "更新过于频繁，请几分钟后更新"
CRAWL_ERROR_MESSAGE = "抓取失败，请稍后重试"
MAX_SQL_EXECUTION_ATTEMPTS = 3


def _validate_text_input(text: str):
    """校验文本入参是否有效。"""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="输入文本不能为空")


def _get_data_status() -> dict:
    """查询最新抓取数据的统计状态。"""
    rows = run_query(
        """
        SELECT
            DATE_FORMAT(MAX(create_time), '%Y-%m-%d %H:%i:%s') AS latest_update_time,
            COUNT(*) AS latest_record_count
        FROM etf_option_data
        """
    )
    status = rows[0] if rows else {}
    return {
        "latest_update_time": status.get("latest_update_time"),
        "latest_record_count": int(status.get("latest_record_count") or 0),
    }


def _get_latest_create_time():
    """获取表内最新数据的创建时间。"""
    rows = run_query("SELECT MAX(create_time) AS latest_create_time FROM etf_option_data")
    value = rows[0].get("latest_create_time") if rows else None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return value


def _build_crawl_failure_response():
    """构造抓取频率受限时的统一响应体。"""
    try:
        status = _get_data_status()
    except Exception:
        status = {
            "latest_update_time": None,
            "latest_record_count": 0,
        }

    return {
        "code": 42901,
        "msg": CRAWL_FAILURE_MESSAGE,
        "data": {
            "total": 0,
            **status,
        },
    }


def _build_crawl_error_response(detail: str = ""):
    """构造抓取失败时的统一响应体。"""
    try:
        status = _get_data_status()
    except Exception:
        status = {
            "latest_update_time": None,
            "latest_record_count": 0,
        }

    msg = f"{CRAWL_ERROR_MESSAGE}：{detail}" if detail else CRAWL_ERROR_MESSAGE
    return {
        "code": 50201,
        "msg": msg,
        "data": {
            "total": 0,
            **status,
        },
    }


def _prepare_query_context(text: str):
    """准备查询链路所需的语义和模板上下文。"""
    normalized_text = SemanticService.normalize_50etf_text(text)
    if normalized_text is None:
        raise HTTPException(status_code=500, detail="模型调用失败，请检查模型配置")

    core_content = SemanticService.extract_core_need_from_text(normalized_text)
    core_content = SemanticService.rule_filter_core_need(core_content)
    results = VectorService.match_user_query(text, top_k=1, core_need=core_content)
    vector_sql = results[0].get("sql") if results else ""
    return normalized_text, core_content, results or [], vector_sql or ""


def _generate_initial_sql(text: str, normalized_text: str, vector_sql: str):
    """生成首条待执行 SQL。"""
    sql = SQLService.generate_sql(text, normalized_text, vector_sql)
    if not sql:
        raise HTTPException(status_code=500, detail="SQL 生成失败")
    return SQLService.finalize_sql(sql, vector_sql)


def _execute_sql_with_retry(text: str, normalized_text: str, vector_sql: str, initial_sql: str):
    """执行 SQL，并在报错时最多重试三次。"""
    baseline_sql = initial_sql
    current_sql = initial_sql
    last_error = ""

    for attempt in range(1, MAX_SQL_EXECUTION_ATTEMPTS + 1):
        try:
            rows = run_query(current_sql)
            return current_sql, rows, attempt
        except HTTPException as exc:
            last_error = str(exc.detail)
            logger.warning("SQL execution attempt %s failed: %s", attempt, last_error)

            if attempt >= MAX_SQL_EXECUTION_ATTEMPTS:
                raise HTTPException(
                    status_code=500,
                    detail=f"查询失败，SQL 执行连续 {MAX_SQL_EXECUTION_ATTEMPTS} 次仍报错：{last_error}",
                ) from exc

            repaired_sql = SQLService.repair_sql(
                user_input=text,
                normalized_text=normalized_text,
                failed_sql=current_sql,
                error_detail=last_error,
            )
            if not repaired_sql:
                raise HTTPException(status_code=500, detail="查询失败，SQL 重试修复失败") from exc

            repaired_sql = SQLService.finalize_sql(repaired_sql, vector_sql)
            if not SQLService.is_safe_retry_sql(baseline_sql, repaired_sql):
                raise HTTPException(status_code=500, detail="查询失败，SQL 重试修复违反原始查询约束") from exc

            current_sql = repaired_sql

    raise HTTPException(status_code=500, detail="查询失败，SQL 重试流程异常结束")


def _build_query_payload(text: str):
    """组装查询接口返回的完整数据载荷。"""
    normalized_text, core_content, results, vector_sql = _prepare_query_context(text)
    initial_sql = _generate_initial_sql(text, normalized_text, vector_sql)
    finalized_sql, rows, _ = _execute_sql_with_retry(text, normalized_text, vector_sql, initial_sql)
    return {
        "normalized_text": normalized_text,
        "core_need": core_content,
        "sql": finalized_sql,
        "rows": rows,
        "total": len(rows),
        "result_mode": SQLService.detect_result_mode(finalized_sql, rows),
        "vector_result": results,
    }


@router.get("/crawl_50etf", summary="抓取并存储 50ETF 期权数据")
def crawl_50etf_data():
    """抓取 50ETF 期权数据并写入数据库。"""
    try:
        option_data = CrawlerService.fetch_option_data()
        inserted_count = CrawlerService.save_data_to_db(option_data)
        return {
            "code": 200,
            "msg": "数据入库成功",
            "data": {
                "total": inserted_count,
                **_get_data_status(),
            },
        }
    except HTTPException as exc:
        logger.warning("crawl_50etf failed with HTTPException: %s", exc.detail)
        if exc.status_code == 429:
            return _build_crawl_failure_response()
        return _build_crawl_error_response(str(exc.detail))
    except Exception as exc:  # pragma: no cover
        logger.exception("crawl_50etf failed")
        return _build_crawl_error_response(str(exc))


@router.get("/data_status", summary="获取 50ETF 数据最新状态")
def get_data_status():
    """获取当前数据库中的 50ETF 数据状态。"""
    try:
        return {
            "code": 200,
            "msg": "处理成功",
            "data": _get_data_status(),
        }
    except HTTPException as exc:
        raise exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/normalize", summary="规范化 50ETF 查询文本")
def normalize_text(request: NormalizeRequest):
    """将用户查询文本转换为规则化描述。"""
    _validate_text_input(request.text)
    try:
        result = SemanticService.normalize_50etf_text(request.text)
        if result is None:
            raise HTTPException(status_code=500, detail="模型调用失败，请检查模型配置")

        return {
            "code": 200,
            "msg": "处理成功",
            "data": {
                "original_text": request.text,
                "normalized_text": result,
            },
        }
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/extract_core", summary="提取核心需求")
def extract_core(request: NormalizeRequest):
    """从用户查询中提取核心需求文本。"""
    _validate_text_input(request.text)
    try:
        normalized_text = SemanticService.normalize_50etf_text(request.text)
        if normalized_text is None:
            raise HTTPException(status_code=500, detail="模型调用失败，请检查模型配置")

        core_content = SemanticService.extract_core_need_from_text(normalized_text)
        core_content = SemanticService.rule_filter_core_need(core_content)
        return {
            "code": 200,
            "msg": "处理成功",
            "data": {
                "original_text": request.text,
                "core_need": core_content,
            },
        }
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/match", summary="匹配最相似模板并返回 SQL")
def match_template(request: NormalizeRequest):
    """基于向量检索结果返回最相似的模板 SQL。"""
    _validate_text_input(request.text)
    try:
        normalized_text, _, results, vector_sql = _prepare_query_context(request.text)
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
                "sql": SQLService.finalize_sql(vector_sql, vector_sql),
            },
        }
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/query", summary="生成 SQL 并查询数据库")
def query_data(request: NormalizeRequest):
    """执行完整查询链路并返回查询结果。"""
    _validate_text_input(request.text)
    try:
        payload = _build_query_payload(request.text)
        payload.pop("vector_result", None)
        return {
            "code": 200,
            "msg": "处理成功",
            "data": payload,
        }
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/query_debug", summary="生成 SQL 并查询数据库（带性能分析）")
def query_data_debug(request: NormalizeRequest):
    """执行带耗时分析的完整查询链路。"""
    _validate_text_input(request.text)
    try:
        start_time = time.time()
        logger.info("Query debug flow started")
        logger.info("User input: %s", request.text)
        logger.info("Start time: %s", time.strftime("%H:%M:%S", time.localtime(start_time)))

        step1_start = time.time()
        normalized_text = SemanticService.normalize_50etf_text(request.text)
        step1_time = time.time() - step1_start
        logger.info("Step 1 normalization: %.3fs", step1_time)
        if normalized_text is None:
            raise HTTPException(status_code=500, detail="模型调用失败，请检查模型配置")

        step2_start = time.time()
        core_content = SemanticService.extract_core_need_from_text(normalized_text)
        core_content = SemanticService.rule_filter_core_need(core_content)
        step2_time = time.time() - step2_start
        logger.info("Step 2 core extraction: %.3fs", step2_time)
        logger.info("Core need: %s", core_content)

        step3_start = time.time()
        results = VectorService.match_user_query(request.text, top_k=1, core_need=core_content)
        step3_time = time.time() - step3_start
        logger.info("Step 3 vector search: %.3fs", step3_time)

        vector_sql = ""
        if results:
            vector_sql = results[0].get("sql") or ""
            logger.info("Matched template: %s", results[0].get("question", ""))
            logger.info("Similarity score: %.4f", results[0].get("score", 0))

        step4_start = time.time()
        initial_sql = _generate_initial_sql(request.text, normalized_text, vector_sql)
        step4_time = time.time() - step4_start
        logger.info("Step 4 SQL generation: %.3fs", step4_time)
        logger.info("Initial SQL: %s", initial_sql)

        step5_start = time.time()
        sql, rows, execution_attempts = _execute_sql_with_retry(request.text, normalized_text, vector_sql, initial_sql)
        step5_time = time.time() - step5_start
        logger.info("Step 5 database query: %.3fs", step5_time)
        logger.info("Final SQL: %s", sql)
        logger.info("SQL execution attempts: %s", execution_attempts)
        logger.info("Returned rows: %s", len(rows))

        total_time = time.time() - start_time
        logger.info("Query debug flow completed in %.3fs", total_time)
        logger.info(
            "Step timings: normalization=%.3fs, core_extraction=%.3fs, "
            "vector_search=%.3fs, sql_generation=%.3fs, database_query=%.3fs",
            step1_time,
            step2_time,
            step3_time,
            step4_time,
            step5_time,
        )

        return {
            "code": 200,
            "msg": "处理成功",
            "data": {
                "normalized_text": normalized_text,
                "core_need": core_content,
                "sql": sql,
                "rows": rows,
                "total": len(rows),
                "result_mode": SQLService.detect_result_mode(sql, rows),
                "performance": {
                    "total_time": round(total_time, 3),
                    "sql_execution_attempts": execution_attempts,
                    "step_times": {
                        "normalization": round(step1_time, 3),
                        "core_extraction": round(step2_time, 3),
                        "vector_search": round(step3_time, 3),
                        "sql_generation": round(step4_time, 3),
                        "database_query": round(step5_time, 3),
                    },
                },
            },
        }
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
