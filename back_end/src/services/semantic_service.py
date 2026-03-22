import json
from src.core.config import get_settings, DATA_DIR
from src.core.llm_client import get_llm_client

RULES_FILE = DATA_DIR / "rules_50etf.json"


def _load_rules():
    """加载规则库文件"""
    try:
        with open(RULES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading rules from {RULES_FILE}: {e}")
        return None


# 加载规则库
RULES_DATA = _load_rules()


class SemanticService:

    @staticmethod
    def normalize_50etf_text(user_input):
        """
        调用 OpenAI 兼容接口规范化用户输入。
        基于 rules_50etf.json 规则库进行解析和转换。
        输出结构化的规则约束信息，而非直接的SQL。

        参数:
            user_input (str): 用户输入的原始文本

        返回:
            str: 结构化的约束文本 或 "无有效50ETF相关信息"
        """

        # 检查输入是否为空
        if not user_input or not user_input.strip():
            return None

        if not RULES_DATA:
            return "错误：规则库加载失败"

        settings = get_settings()

        # 提取规则库的关键部分构建提示词
        basic_rules = RULES_DATA.get("基础规则", {})
        advanced_rules = RULES_DATA.get("进阶规则", {})

        invalid_words = basic_rules.get("无效词过滤", [])
        option_type_map = basic_rules.get("期权类型映射", {})
        field_map = basic_rules.get("指标字段映射", {})
        time_map = basic_rules.get("时间条件映射", {})
        numeric_template = basic_rules.get("数值条件模板", {})
        sort_map = basic_rules.get("排序规则映射", {})
        fuzzy_map = basic_rules.get("模糊查询映射", {})
        exception_thresholds = advanced_rules.get("异常值阈值", {})

        # 构建动态系统提示词
        system_prompt = f"""
    你是一个金融领域意图识别与规则匹配引擎，处于"智能问数系统"的第一阶段。
    你的核心任务是：根据【规则库】对用户输入进行解析，提取硬性业务约束，**绝对不要生成完整的SQL语句**。
    
    注意：
    1. 本系统仅针对单一标的期权数据，无需输出任何关于标的或 etf_type 的约束，默认所有查询都是同一标的。
    2. **纠错机制**：如果你发现用户输入中有明显的错别字或模糊表达（如"认够"->"认购"，"成交亮"->"成交量"），必须进行自动纠错，并在输出中显式说明。
    3. **数值条件纠错**：如果数值条件的字段名有错别字（如"成交亮"），必须在输出中注明纠错过程。
    4. **关键词替换**：核心需求（纠错后）中的关键词必须使用规则库的标准词进行替换（例如"看涨"->"购"，"买权"->"购"，"涨跌幅"/"涨幅"统一为"涨跌幅"，"量能"统一为"成交量"，"末日论"统一为"末日轮"）。
    5. **禁止虚空构造**：核心需求（纠错后）只能由用户输入或规则匹配约束中已有的词汇构成，不允许新增用户未提及也未被规则映射出的指标或条件词汇。

    请严格参考以下规则库数据：
    【1. 预处理规则】
    - 无效词库：{json.dumps(invalid_words, ensure_ascii=False)}
    
    【2. 核心映射规则】
    - 期权类型：{json.dumps(option_type_map, ensure_ascii=False)}
    - 指标字段：{json.dumps(field_map, ensure_ascii=False)}
    - 时间条件：{json.dumps(time_map, ensure_ascii=False)}
    - 排序规则：{json.dumps(sort_map, ensure_ascii=False)}
    - 模糊查询：{json.dumps(fuzzy_map, ensure_ascii=False)}
    - 异常值阈值：{json.dumps(exception_thresholds, ensure_ascii=False)}
    - 数值条件模板：{json.dumps(numeric_template, ensure_ascii=False)}

    【3. 输出格式要求】
    请严格按照以下格式输出（仅输出内容，不要markdown代码块）：
    
    【核心需求（纠错后）】
    <将纠错后的核心意图文本，单独输出为一行，并将同义词替换为规则库标准词，例如："本周到期的购期权，涨跌幅最高，成交量>80000">
    
    【规则匹配结果】
    1. 无效词过滤：去掉"<识别到的无效词>"，核心需求（纠错后）为"<清洗并纠错后的意图>"；
    2. 期权类型约束：<描述类型限制，如果有纠错，请注明：经大模型语义纠错，"<原词>"匹配规则库"<标准词>"，需过滤 contract_name LIKE '%...%'>；
    3. <具体条件约束>：<描述时间/数值/排序/模糊查询的具体规则，如果有纠错，请注明：经大模型语义纠错，"<原词>"匹配规则库"<标准词>"，需...>；
    4. 异常值约束：<根据涉及的字段，引用异常值阈值规则，如：持仓量必须>0>；
    5. 字段约束：<列出涉及的数据库字段英文名> 等字段（不要包含 etf_type）。

    【示例】
    用户输入："帮我找一下持仓量最大的沽期权"
    输出：
    【核心需求（纠错后）】
    持仓量最大的沽期权
    【规则匹配结果】
    1. 无效词过滤：去掉"帮我找一下"，核心需求（纠错后）为"持仓量最大的沽期权"；
    2. 期权类型约束："沽"匹配规则库，需过滤 contract_name LIKE '%沽%'；
    3. 排序约束："持仓量最大"匹配规则，需按 position_volume 降序排列且仅取1条（ORDER BY position_volume DESC LIMIT 1）；
    4. 异常值约束：持仓量上限为1000000000，且通常需>0；
    5. 字段约束：position_volume, contract_name 等字段。

    用户输入："帮我查查购期权，成交亮大于100"
    输出：
    【核心需求（纠错后）】
    购期权，成交量大于100
    【规则匹配结果】
    1. 无效词过滤：去掉"帮我查查"，核心需求（纠错后）为"购期权，成交量大于100"；
    2. 期权类型约束：经大模型语义纠错，"认够"匹配规则库"购"，需过滤 contract_name LIKE '%购%'；
    3. 数值条件约束：经大模型语义纠错，"成交亮"匹配规则库"成交量"，需 volume > 100；
    4. 异常值约束：成交量上限为1000000000，且通常需>0；
    5. 字段约束：contract_name, volume 等字段。

    用户输入："今天天气真好"
    输出：
    【规则匹配结果】
    1. 无效词过滤：全文均为无效内容；
    2. 结果：无有效相关信息。
    """

        try:
            client = get_llm_client()
            response = client.chat.completions.create(
                model=settings.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                temperature=settings.temperature,
                extra_body={"enable_thinking": settings.thinking_enable},
            )
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            return "模型未返回有效内容"
        except Exception as e:
            # 捕获连接错误（如服务未启动）或其他异常
            print(f"\n错误: 发生异常 - {str(e)}")
            return None

    @staticmethod
    def rule_filter_core_need(core_need):
        """
        基于规则库对核心需求文本进行清洗与标准化。
        参数:
            core_need (str): 核心需求文本。
        返回:
            str | None: 规则过滤后的核心需求文本。
        """
        if not core_need:
            return core_need
        if not RULES_DATA:
            return core_need
        basic_rules = RULES_DATA.get("基础规则", {})
        invalid_words = basic_rules.get("无效词过滤", [])
        option_type_map = basic_rules.get("期权类型映射", {})
        text = core_need
        for word in sorted(invalid_words, key=len, reverse=True):
            if word:
                text = text.replace(word, "")
        for key, value in sorted(option_type_map.items(), key=lambda x: len(x[0]), reverse=True):
            if key and value:
                text = text.replace(key, value)
        while "认认购" in text:
            text = text.replace("认认购", "认购")
        while "认购认购" in text:
            text = text.replace("认购认购", "认购")
        while "认认沽" in text:
            text = text.replace("认认沽", "认沽")
        while "认沽认沽" in text:
            text = text.replace("认沽认沽", "认沽")
        text = " ".join(text.split())
        while "，，" in text:
            text = text.replace("，，", "，")
        while ",," in text:
            text = text.replace(",,", ",")
        text = text.strip(" ，,;；")
        return text

    @staticmethod
    def extract_core_need_from_text(result):
        """
        从规则匹配结果中提取"核心需求（纠错后）"单行文本。
        参数:
            result (str): 规则匹配的完整输出文本。
        返回:
            str | None: 纠错后的核心需求文本，或空值。
        """
        if not result:
            return None
        lines = result.splitlines()
        for i, line in enumerate(lines):
            if "【核心需求（纠错后）】" in line:
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                while j < len(lines):
                    s = lines[j].strip()
                    if s and not s.startswith("【"):
                        return s
                    j += 1
                break
        return None

    @staticmethod
    def extract_core_need(user_input):
        """
        从规则匹配结果中提取"核心需求（纠错后）"单行文本。
        参数:
            user_input (str): 用户输入的原始文本。
        返回:
            str | None: 纠错后的核心需求文本，或空值。
        """
        result = SemanticService.normalize_50etf_text(user_input)
        core_need = SemanticService.extract_core_need_from_text(result)
        return SemanticService.rule_filter_core_need(core_need)
