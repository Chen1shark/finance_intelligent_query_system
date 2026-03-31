import re

from src.core.config import get_settings
from src.core.llm_client import get_llm_client

_SINGLE_ROW_SQL_PATTERNS = (
    re.compile(r"\blimit\s+1\b", re.IGNORECASE),
    re.compile(r"\bcontract_code\s*=", re.IGNORECASE),
    re.compile(r"\bcontract_name\s*=", re.IGNORECASE),
)
_SELECT_CLAUSE_PATTERN = re.compile(r"^\s*select\s+(distinct\s+)?(.+?)\s+from\s+", re.IGNORECASE | re.DOTALL)


class SQLService:
    """负责 SQL 提示词构建、清洗与结果模式判断。"""

    @staticmethod
    def build_sql_prompt(user_input, normalized_text, vector_result):
        """构建用于生成 SQL 的提示词。

        Args:
            user_input: 用户原始查询文本。
            normalized_text: 规则层输出的规范化文本。
            vector_result: 向量检索返回的模板 SQL 或辅助信息。

        Returns:
            str: 提供给大模型的完整提示词。
        """
        return f"""请你根据以下三类输入生成可执行的 MySQL 查询 SQL 语句，务必严格遵守输入优先级和约束要求。

#### 优先级定义（核心准则）
1. 规则匹配结果（normalized_text）为最高优先级，必须 100% 严格遵守，任何情况下不得违背。
2. 向量匹配结果仅作为重要参考，若其中包含的 SQL 模板、字段或数据条件与规则冲突，一律以规则为准。
3. 用户原始输入仅作为补充参考，仅当规则和向量匹配中存在明确遗漏时才可少量补充。

#### 一、用户原始输入（补充参考）
{user_input}

#### 二、规则匹配结果（normalized_text，最高优先级）
{normalized_text}

#### 三、向量匹配结果（重要参考）
{vector_result}

#### 生成要求
1. 严格遵循优先级规则，normalized_text 中的所有约束都不可违背。
2. 若向量模板中存在字段错误、缺失或多余字段，自动按 normalized_text 修正。
3. 表名必须使用 etf_option_data。
4. 生成的 SQL 仅包含可直接执行的 MySQL SELECT 语句，不要输出任何解释、注释或 Markdown。
5. 若查询目标最终收敛到单条期权合约（例如 LIMIT 1、唯一合约代码、唯一合约名称），必须返回该条期权的全部字段，使用 SELECT * 或等价的全字段查询。
6. 多条结果列表查询仍按条件筛选返回，不要无故扩大结果范围。
"""

    @staticmethod
    def clean_sql_output(text):
        """清洗大模型返回的 SQL 文本。

        Args:
            text: 大模型原始输出，可能包含代码块或多余前缀。

        Returns:
            str | None: 可直接执行的 SQL 文本；当输入为空时原样返回。
        """
        if not text:
            return text

        sql_text = text.strip()
        if "```" in sql_text:
            parts = [part.strip() for part in sql_text.split("```") if part.strip()]
            if parts:
                sql_text = parts[-1]

        for prefix in ("sql:", "SQL:", "SQL：", "sql："):
            if sql_text.startswith(prefix):
                sql_text = sql_text[len(prefix):].strip()
                break

        if sql_text.lower().startswith("sql"):
            sql_text = sql_text[3:].lstrip(":：").strip()

        if sql_text.lower().startswith("select"):
            return sql_text

        index = sql_text.lower().find("select")
        if index >= 0:
            return sql_text[index:].strip()

        return sql_text

    @staticmethod
    def is_single_row_query(sql_text=None, template_sql=None):
        """判断 SQL 是否会收敛为单条结果。

        Args:
            sql_text: 当前生成的 SQL 文本。
            template_sql: 向量匹配出的模板 SQL 文本。

        Returns:
            bool: 任一 SQL 命中单行查询规则时返回 ``True``。
        """
        for candidate in (sql_text or "", template_sql or ""):
            if any(pattern.search(candidate) for pattern in _SINGLE_ROW_SQL_PATTERNS):
                return True
        return False

    @staticmethod
    def force_select_all_fields(sql_text):
        """将单行查询改写为全字段查询。

        Args:
            sql_text: 原始 SQL 文本。

        Returns:
            str | None: 改写后的全字段 SQL；当 SQL 无法识别或为空时原样返回。
        """
        if not sql_text:
            return sql_text

        match = _SELECT_CLAUSE_PATTERN.match(sql_text)
        if not match:
            return sql_text

        distinct_prefix = "DISTINCT " if match.group(1) else ""
        remainder = sql_text[match.end():].lstrip()
        return f"SELECT {distinct_prefix}* FROM {remainder}"

    @staticmethod
    def finalize_sql(sql_text, template_sql=None):
        """对生成 SQL 做最终清洗和收尾修正。

        Args:
            sql_text: 当前生成的 SQL 文本。
            template_sql: 向量匹配出的模板 SQL 文本。

        Returns:
            str | None: 清洗后的最终 SQL；若识别为单行查询则自动改写为全字段查询。
        """
        if not sql_text:
            return sql_text

        cleaned_sql = SQLService.clean_sql_output(sql_text)
        if SQLService.is_single_row_query(cleaned_sql, template_sql):
            return SQLService.force_select_all_fields(cleaned_sql)
        return cleaned_sql

    @staticmethod
    def detect_result_mode(sql_text, rows):
        """根据 SQL 和结果集判断前端展示模式。

        Args:
            sql_text: 最终执行的 SQL 文本。
            rows: 数据库查询结果列表。

        Returns:
            str: 单条明细返回 ``detail``，否则返回 ``list``。
        """
        if len(rows) == 1 and SQLService.is_single_row_query(sql_text=sql_text):
            return "detail"
        return "list"

    @staticmethod
    def generate_sql(user_input, normalized_text, vector_result=None, model=None):
        """调用大模型生成 SQL 语句。

        Args:
            user_input: 用户原始查询文本。
            normalized_text: 规则层输出的规范化文本。
            vector_result: 向量检索返回的模板 SQL 或辅助信息。
            model: 可选的模型名称覆盖项。

        Returns:
            str | None: 清洗后的 SQL 语句；当模型未返回内容时返回 ``None``。
        """
        settings = get_settings()
        prompt = SQLService.build_sql_prompt(user_input, normalized_text, vector_result or "")
        client = get_llm_client()
        response = client.chat.completions.create(
            model=model or settings.model_name,
            messages=[
                {"role": "system", "content": "你是一个 MySQL SQL 生成器，只输出 SQL 语句本身。"},
                {"role": "user", "content": prompt},
            ],
            temperature=settings.temperature,
            extra_body={"enable_thinking": settings.thinking_enable},
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return SQLService.clean_sql_output(response.choices[0].message.content)
        return None
