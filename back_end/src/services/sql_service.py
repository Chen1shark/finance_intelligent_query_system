from src.core.config import get_settings
from src.core.llm_client import get_llm_client


class SQLService:

    @staticmethod
    def build_sql_prompt(user_input, normalized_text, vector_result):
        return f"""请你根据以下三类输入生成可执行的MySQL查询SQL语句，务必严格遵守输入的优先级和约束要求：
#### 优先级定义（核心准则）
1. 规则匹配结果（normalized_text）为最高优先级，必须100%严格遵守，任何情况下不得违背；
2. 向量匹配接口结果仅作为重要参考，若其包含的SQL模板/字段/数据条件与规则冲突，一律以规则为准；
3. 用户原始输入仅作为补充参考，仅当规则和向量匹配中存在明确遗漏时可少量补充，无遗漏则无需参考。

#### 一、用户原始输入（补充参考）
{user_input}

#### 二、规则匹配结果（normalized_text，最高优先级，必须严格遵守）
{normalized_text}

#### 三、向量匹配接口结果（重要参考，冲突时以规则为准）
{vector_result}

#### 生成要求
1. 严格遵循优先级规则，normalized_text中的所有约束不可违背，向量模板仅参考语法范式，用户输入仅补充明确遗漏；
2. 若向量模板中存在字段错误/缺失/过多（如包含normalized_text未指定的字段），自动忽略并按normalized_text修正；
3. 表名必须使用 etf_option_data；
4. 生成的SQL语句仅包含MySQL合法语法，可直接执行，无多余注释/解释，仅输出SQL语句本身；
5. 需贴合期权数据场景，确保字段、数值条件与normalized_text中的约束完全一致。"""

    @staticmethod
    def clean_sql_output(text):
        if not text:
            return text
        s = text.strip()
        if "```" in s:
            parts = [p.strip() for p in s.split("```") if p.strip()]
            if parts:
                s = parts[-1]
        for prefix in ("sql:", "SQL:", "SQL：", "sql："):
            if s.startswith(prefix):
                s = s[len(prefix):].strip()
                break
        if s.lower().startswith("sql"):
            s = s[3:].lstrip(":：").strip()
        if s.lower().startswith("select"):
            return s
        idx = s.lower().find("select")
        if idx >= 0:
            return s[idx:].strip()
        return s.strip()

    @staticmethod
    def generate_sql(user_input, normalized_text, vector_result=None, model=None):
        settings = get_settings()
        if vector_result is None:
            vector_result = ""
        prompt = SQLService.build_sql_prompt(user_input, normalized_text, vector_result)
        client = get_llm_client()
        response = client.chat.completions.create(
            model=model or settings.model_name,
            messages=[
                {"role": "system", "content": "你是一个MySQL SQL生成器，只输出SQL语句本身。"},
                {"role": "user", "content": prompt},
            ],
                temperature=settings.temperature,
                extra_body={"enable_thinking": settings.thinking_enable},
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return SQLService.clean_sql_output(response.choices[0].message.content)
        return None
