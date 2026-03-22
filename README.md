# 50ETF 期权智能问数系统

> 基于 FastAPI + LLM + FAISS 的金融期权数据智能查询后端系统

本系统面向 50ETF 期权数据，支持用户以**自然语言**提问，后端自动完成语义理解、规则匹配、向量检索、SQL 生成与数据库查询，最终返回结构化结果。

---

## 目录

- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [模块说明](#模块说明)
- [系统流程](#系统流程)
- [快速开始](#快速开始)
- [环境变量配置](#环境变量配置)
- [数据库准备](#数据库准备)
- [API 接口文档](#api-接口文档)
- [前端调用指南](#前端调用指南)
- [数据库表结构](#数据库表结构)
- [注意事项](#注意事项)

---

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| 大语言模型 | 阿里云 DashScope（Qwen3.5-Flash）|
| 向量嵌入 | text-embedding-v4（阿里云） |
| 向量检索 | FAISS（Facebook AI Similarity Search） |
| 数据库 | MySQL 8.0+（PyMySQL 驱动） |
| 数据源 | 东方财富期权行情接口 |
| 配置管理 | pydantic-settings + python-dotenv |
| Python 版本 | 3.8+ |

---

## 项目结构

```
finance_intelligent_query_system/
│
├── .env                              # 环境变量（API密钥、数据库凭证，不提交到Git）
├── .env.example                      # 环境变量模板（供新开发者参考）
├── .gitignore                        # Git忽略规则
├── requirements.txt                  # Python依赖清单
├── README.md                         # 项目文档（本文件）
│
├── src/                              # 主应用源代码
│   ├── __init__.py
│   ├── main.py                       # FastAPI 应用入口 & Uvicorn 启动
│   │
│   ├── api/                          # API 路由层
│   │   ├── __init__.py
│   │   ├── routes.py                 # 5 个 API 端点定义
│   │   └── schemas.py                # Pydantic 请求/响应模型
│   │
│   ├── services/                     # 业务逻辑层（核心服务）
│   │   ├── __init__.py
│   │   ├── crawler_service.py        # 爬虫服务 — 东方财富数据抓取与入库
│   │   ├── semantic_service.py       # 语义理解服务 — LLM规范化 + 规则匹配
│   │   ├── vector_service.py         # 向量检索服务 — FAISS相似度匹配
│   │   └── sql_service.py            # SQL生成服务 — LLM生成MySQL查询
│   │
│   ├── core/                         # 核心基础设施层
│   │   ├── __init__.py
│   │   ├── config.py                 # 配置管理（pydantic-settings，从.env加载）
│   │   ├── database.py               # 数据库连接管理 + SQL执行工具
│   │   └── llm_client.py             # OpenAI 兼容客户端封装（单例）
│   │
│   └── utils/                        # 工具函数层
│       ├── __init__.py
│       └── data_parser.py            # 数据类型安全转换（safe_decimal/safe_int）
│
├── data/                             # 数据文件
│   ├── rules_50etf.json              # 业务规则库（期权类型映射、字段映射等）
│   ├── vector_store.json             # 向量数据库（标准问题 + SQL模板 + 嵌入向量）
│   └── schema/
│       └── sql.sql                   # MySQL 建表语句
│
└── tests/                            # 测试目录（预留）
    └── __init__.py
```

---

## 模块说明

### 核心基础设施层 `src/core/`

| 文件 | 职责 |
|------|------|
| `config.py` | 使用 `pydantic-settings` 从 `.env` 加载所有配置项，提供类型安全的 `Settings` 单例 |
| `database.py` | 封装 PyMySQL 连接创建、上下文管理器、`run_query()` 安全执行 SELECT |
| `llm_client.py` | 封装 OpenAI 兼容客户端，全局单例，避免重复初始化 |

### 业务服务层 `src/services/`

| 文件 | 类名 | 职责 |
|------|------|------|
| `crawler_service.py` | `CrawlerService` | 从东方财富抓取50ETF期权数据，解析JSONP，批量写入MySQL |
| `semantic_service.py` | `SemanticService` | 调用LLM对用户输入进行规范化、纠错、规则匹配，提取核心需求 |
| `vector_service.py` | `VectorService` | 管理FAISS向量索引，启动时重建嵌入，根据核心需求匹配最相似SQL模板 |
| `sql_service.py` | `SQLService` | 综合规则匹配和向量匹配结果，调用LLM生成最终可执行的MySQL语句 |

### API 路由层 `src/api/`

| 文件 | 职责 |
|------|------|
| `schemas.py` | 定义 `NormalizeRequest`（请求体：`{"text": "..."}`) |
| `routes.py` | 注册 5 个 API 端点，调用服务层，返回统一格式响应 |

### 工具层 `src/utils/`

| 文件 | 职责 |
|------|------|
| `data_parser.py` | `safe_decimal()` 和 `safe_int()` — 安全处理爬虫数据中的空值与异常值 |

---

## 系统流程

### 主查询流程（`/api/query` 端点）

```
用户自然语言输入
       │
       ▼
┌─────────────────────┐
│  1. 语义规范化       │  SemanticService.normalize_50etf_text()
│     LLM + 规则库     │  基于 rules_50etf.json 进行意图识别、
│                      │  纠错（如"认够"→"认购"）、关键词标准化
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  2. 核心需求提取     │  SemanticService.extract_core_need_from_text()
│     + 规则过滤       │  SemanticService.rule_filter_core_need()
│                      │  提取"核心需求（纠错后）"单行文本
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  3. 向量相似度检索   │  VectorService.match_user_query()
│     FAISS            │  将核心需求向量化，与模板库做余弦相似度匹配
│                      │  返回最相似的标准问题及其SQL模板
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  4. SQL 生成         │  SQLService.generate_sql()
│     LLM              │  综合：用户原文 + 规则匹配结果 + 向量SQL模板
│                      │  由LLM生成最终可执行的MySQL语句
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  5. 数据库查询       │  database.run_query()
│     MySQL            │  执行生成的SELECT语句，返回结果集
└──────────┬──────────┘
           │
           ▼
     返回结构化JSON响应
```

### 启动流程

```
应用启动 (python -m src.main)
       │
       ▼
  加载 .env 配置
       │
       ▼
  创建 FastAPI 应用
       │
       ▼
  lifespan startup:
  VectorService.rebuild_vector_store_embeddings()
  → 读取 vector_store.json
  → 对每个标准问题调用 embedding API 重新生成向量
  → 写回文件 + 缓存到内存
       │
       ▼
  注册 API 路由（5个端点）
       │
       ▼
  Uvicorn 监听 0.0.0.0:8000
```

---

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd finance_intelligent_query_system
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制模板
cp .env.example .env

# 编辑 .env，填入真实值
# 必须配置：API_KEY（阿里云DashScope密钥）、DB_PASSWORD（MySQL密码）
```

### 4. 初始化数据库

```bash
# 登录 MySQL 执行建表语句
mysql -u root -p < data/schema/sql.sql
```

### 5. 启动服务

```bash
python -m src.main
```

启动后：
- 服务地址：`http://127.0.0.1:8000`
- Swagger 文档：`http://127.0.0.1:8000/docs`
- ReDoc 文档：`http://127.0.0.1:8000/redoc`

---

## 环境变量配置

在项目根目录创建 `.env` 文件，所有配置项如下：

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `API_KEY` | 阿里云 DashScope API 密钥 | （无） | **是** |
| `BASE_URL` | LLM API 基础地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 否 |
| `MODEL_NAME` | 对话模型名称 | `qwen3.5-flash` | 否 |
| `EMBED_MODEL` | 向量嵌入模型名称 | `text-embedding-v4` | 否 |
| `TEMPERATURE` | LLM 温度参数 | `0.0` | 否 |
| `THINKIN_ENABLE` | 是否启用思考模式 | `False` | 否 |
| `DB_HOST` | MySQL 主机地址 | `127.0.0.1` | 否 |
| `DB_PORT` | MySQL 端口 | `3306` | 否 |
| `DB_USER` | MySQL 用户名 | `root` | 否 |
| `DB_PASSWORD` | MySQL 密码 | （无） | **是** |
| `DB_NAME` | MySQL 数据库名 | `eastmoney_db` | 否 |
| `TARGET_URL` | 东方财富期权行情接口地址 | `http://push2.eastmoney.com/api/qt/clist/get` | 否 |
| `PROJECT_NAME` | 项目名称（Swagger标题） | `50ETF期权智能问数系统` | 否 |
| `PROJECT_VERSION` | 项目版本号 | `1.0.0` | 否 |
| `API_PREFIX` | API 路由前缀 | `/api` | 否 |

---

## 数据库准备

### 创建数据库和表

```sql
CREATE DATABASE IF NOT EXISTS eastmoney_db DEFAULT CHARSET utf8mb4;
USE eastmoney_db;

CREATE TABLE IF NOT EXISTS etf_option_data (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    contract_code VARCHAR(20) NOT NULL COMMENT '合约代码',
    contract_name VARCHAR(50) NOT NULL COMMENT '合约名称',
    latest_price DECIMAL(10,3) COMMENT '最新价',
    price_change DECIMAL(10,3) COMMENT '涨跌额',
    price_change_rate DECIMAL(10,2) COMMENT '涨跌幅(%)',
    volume INT COMMENT '成交量(手)',
    turnover DECIMAL(15,2) COMMENT '成交额(元)',
    position_volume INT COMMENT '持仓量(手)',
    strike_price DECIMAL(10,3) COMMENT '行权价',
    remain_days INT COMMENT '剩余天数',
    position_change INT COMMENT '持仓量日增减',
    settlement_price_yesterday DECIMAL(10,3) COMMENT '昨日结算价',
    open_price_today DECIMAL(10,3) COMMENT '今日开盘价',
    etf_type VARCHAR(10) NOT NULL COMMENT 'ETF类型(50ETF)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据入库时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

完整建表语句见 `data/schema/sql.sql`。

---

## API 接口文档

所有接口基础路径：`http://127.0.0.1:8000`

统一响应格式：
```json
{
    "code": 200,
    "msg": "处理成功",
    "data": { ... }
}
```

错误响应：
```json
{
    "detail": "错误描述信息"
}
```

---

### 1. GET `/api/crawl_50etf` — 爬取期权数据（调试用）

触发从东方财富抓取最新 50ETF 期权数据并写入数据库。

**请求**

```
GET http://127.0.0.1:8000/api/crawl_50etf
```

无请求参数。

**前端调用示例**

```javascript
const response = await fetch('http://127.0.0.1:8000/api/crawl_50etf');
const result = await response.json();
console.log(result);
```

**成功响应**

```json
{
    "code": 200,
    "msg": "数据入库成功",
    "data": {
        "total": 192
    }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.total` | `int` | 入库的数据条数 |

---

### 2. POST `/api/normalize` — 语义规范化（调试用）

使用 LLM + 规则库对用户输入文本进行规范化处理。

**请求**

```
POST http://127.0.0.1:8000/api/normalize
Content-Type: application/json

{
    "text": "帮我找一下持仓量最大的沽期权"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | `string` | 是 | 用户原始输入文本 |

**前端调用示例**

```javascript
const response = await fetch('http://127.0.0.1:8000/api/normalize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: '帮我找一下持仓量最大的沽期权' })
});
const result = await response.json();
console.log(result);
```

**成功响应**

```json
{
    "code": 200,
    "msg": "处理成功",
    "data": {
        "original_text": "帮我找一下持仓量最大的沽期权",
        "normalized_text": "【核心需求（纠错后）】\n持仓量最大的沽期权\n【规则匹配结果】\n1. 无效词过滤：去掉\"帮我找一下\"..."
    }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.original_text` | `string` | 用户原始输入 |
| `data.normalized_text` | `string` | LLM规范化后的完整结构化文本 |

---

### 3. POST `/api/extract_core` — 核心需求提取（调试用）

规范化输入后，提取纠错后的核心需求单行文本。

**请求**

```
POST http://127.0.0.1:8000/api/extract_core
Content-Type: application/json

{
    "text": "帮我查查购期权，成交亮大于100"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | `string` | 是 | 用户原始输入文本 |

**前端调用示例**

```javascript
const response = await fetch('http://127.0.0.1:8000/api/extract_core', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: '帮我查查购期权，成交亮大于100' })
});
const result = await response.json();
console.log(result);
```

**成功响应**

```json
{
    "code": 200,
    "msg": "处理成功",
    "data": {
        "original_text": "帮我查查购期权，成交亮大于100",
        "core_need": "购期权，成交量大于100"
    }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.original_text` | `string` | 用户原始输入 |
| `data.core_need` | `string \| null` | 纠错后的核心需求文本 |

---

### 4. POST `/api/match` — 向量匹配（调试用）

完成规范化 + 核心需求提取后，通过 FAISS 向量检索匹配最相似的标准问题模板。

**请求**

```
POST http://127.0.0.1:8000/api/match
Content-Type: application/json

{
    "text": "持仓量最大的沽期权"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | `string` | 是 | 用户原始输入文本 |

**前端调用示例**

```javascript
const response = await fetch('http://127.0.0.1:8000/api/match', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: '持仓量最大的沽期权' })
});
const result = await response.json();
console.log(result);
```

**成功响应**

```json
{
    "code": 200,
    "msg": "处理成功",
    "data": {
        "normalized_text": "【核心需求（纠错后）】\n持仓量最大的沽期权...",
        "core_need": "持仓量最大的沽期权",
        "score": 0.9523,
        "question": "持仓量最大的认沽期权",
        "sql": "SELECT * FROM etf_option_data WHERE contract_name LIKE '%沽%' ORDER BY position_volume DESC LIMIT 1"
    }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.normalized_text` | `string` | LLM规范化后的完整文本 |
| `data.core_need` | `string` | 纠错后的核心需求 |
| `data.score` | `float` | 向量余弦相似度（0~1，越高越相似） |
| `data.question` | `string` | 匹配到的标准问题模板 |
| `data.sql` | `string` | 模板对应的SQL语句 |

---

### 5. POST `/api/query` — 智能查询（主接口，供前端使用）

**这是前端调用的主接口**。完成完整查询流程：语义规范化 → 核心需求提取 → 向量检索 → SQL生成 → 数据库查询，返回最终数据。

**请求**

```
POST http://127.0.0.1:8000/api/query
Content-Type: application/json

{
    "text": "帮我找一下持仓量最大的沽期权"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | `string` | 是 | 用户自然语言提问 |

**前端调用示例**

```javascript
// 推荐的前端调用方式
async function queryETFData(userQuestion) {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: userQuestion })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '请求失败');
        }

        const result = await response.json();

        if (result.code === 200) {
            console.log('规范化文本:', result.data.normalized_text);
            console.log('核心需求:', result.data.core_need);
            console.log('生成的SQL:', result.data.sql);
            console.log('查询结果:', result.data.rows);
            console.log('结果总数:', result.data.total);
            return result.data;
        }
    } catch (error) {
        console.error('查询失败:', error.message);
    }
}

// 调用
queryETFData('帮我找一下持仓量最大的沽期权');
```

**Axios 调用示例**

```javascript
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000';

async function queryETFData(text) {
    const { data } = await axios.post(`${API_BASE}/api/query`, { text });
    return data;
}
```

**成功响应**

```json
{
    "code": 200,
    "msg": "处理成功",
    "data": {
        "normalized_text": "【核心需求（纠错后）】\n持仓量最大的沽期权\n【规则匹配结果】\n...",
        "core_need": "持仓量最大的沽期权",
        "sql": "SELECT * FROM etf_option_data WHERE contract_name LIKE '%沽%' AND position_volume > 0 ORDER BY position_volume DESC LIMIT 1",
        "rows": [
            {
                "id": 45,
                "contract_code": "10007328",
                "contract_name": "50ETF沽3月3000",
                "latest_price": 0.123,
                "price_change": -0.005,
                "price_change_rate": -3.91,
                "volume": 18542,
                "turnover": 2283468.0,
                "position_volume": 285634,
                "strike_price": 3.0,
                "remain_days": 15,
                "position_change": 1234,
                "settlement_price_yesterday": 0.128,
                "open_price_today": 0.126,
                "etf_type": "50ETF",
                "create_time": "2025-03-22T19:30:00"
            }
        ],
        "total": 1
    }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.normalized_text` | `string` | LLM 规范化后的完整结构化文本 |
| `data.core_need` | `string \| null` | 纠错后的核心需求文本 |
| `data.sql` | `string` | 最终生成并执行的 SQL 语句 |
| `data.rows` | `array` | 查询结果数组，每个元素为一条期权数据记录 |
| `data.total` | `int` | 查询结果总条数 |

**rows 中每条记录的字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int` | 主键 |
| `contract_code` | `string` | 合约代码 |
| `contract_name` | `string` | 合约名称（如"50ETF购3月3000"） |
| `latest_price` | `float` | 最新价（元） |
| `price_change` | `float` | 涨跌额（元） |
| `price_change_rate` | `float` | 涨跌幅（%） |
| `volume` | `int` | 成交量（手） |
| `turnover` | `float` | 成交额（元） |
| `position_volume` | `int` | 持仓量（手） |
| `strike_price` | `float` | 行权价（元） |
| `remain_days` | `int` | 剩余天数 |
| `position_change` | `int` | 持仓量日增减 |
| `settlement_price_yesterday` | `float` | 昨日结算价（元） |
| `open_price_today` | `float` | 今日开盘价（元） |
| `etf_type` | `string` | ETF类型（"50ETF"） |
| `create_time` | `string` | 数据入库时间（ISO格式） |

---

## 前端调用指南

### 基础配置

```javascript
// config.js
const API_CONFIG = {
    baseURL: 'http://127.0.0.1:8000',
    timeout: 30000,  // 30秒超时（LLM调用可能较慢）
};
```

### 跨域说明

如果前端与后端不在同一域名/端口，需要在后端添加 CORS 中间件。当前版本未内置 CORS，如需开启可在 `src/main.py` 中添加：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 生产环境请限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 接口调用路径总览

| 用途 | 方法 | 路径 | 场景 |
|------|------|------|------|
| 爬取数据 | `GET` | `/api/crawl_50etf` | 管理后台触发数据更新 |
| 语义规范化 | `POST` | `/api/normalize` | 调试：查看LLM规范化结果 |
| 核心需求提取 | `POST` | `/api/extract_core` | 调试：查看纠错后核心需求 |
| 向量匹配 | `POST` | `/api/match` | 调试：查看向量检索结果 |
| **智能查询** | `POST` | `/api/query` | **前端主接口** |

> 前端日常使用只需调用 `/api/query` 一个接口，其他接口用于开发调试。

### 错误处理建议

```javascript
async function safeQuery(text) {
    try {
        const res = await fetch('http://127.0.0.1:8000/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        if (res.status === 400) {
            return { error: '输入文本不能为空' };
        }
        if (res.status === 404) {
            return { error: '未匹配到相关模板' };
        }
        if (res.status === 500) {
            const err = await res.json();
            return { error: err.detail || '服务器内部错误' };
        }

        return await res.json();
    } catch (e) {
        return { error: '网络连接失败，请检查后端服务是否启动' };
    }
}
```

---

## 数据库表结构

数据库：`eastmoney_db`  
数据表：`etf_option_data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT (PK, AUTO_INCREMENT) | 主键 |
| `contract_code` | VARCHAR(20) | 合约代码 |
| `contract_name` | VARCHAR(50) | 合约名称 |
| `latest_price` | DECIMAL(10,3) | 最新价 |
| `price_change` | DECIMAL(10,3) | 涨跌额 |
| `price_change_rate` | DECIMAL(10,2) | 涨跌幅(%) |
| `volume` | INT | 成交量(手) |
| `turnover` | DECIMAL(15,2) | 成交额(元) |
| `position_volume` | INT | 持仓量(手) |
| `strike_price` | DECIMAL(10,3) | 行权价 |
| `remain_days` | INT | 剩余天数 |
| `position_change` | INT | 持仓量日增减 |
| `settlement_price_yesterday` | DECIMAL(10,3) | 昨日结算价 |
| `open_price_today` | DECIMAL(10,3) | 今日开盘价 |
| `etf_type` | VARCHAR(10) | ETF类型标识 |
| `create_time` | DATETIME | 数据入库时间 |

---

## 注意事项

1. **启动耗时**：应用启动时会调用 embedding API 对向量库中所有标准问题重新生成嵌入向量，可能需要 5~15 秒。

2. **API 密钥**：确保 `.env` 中的 `API_KEY` 有效且有足够配额（阿里云 DashScope），否则语义理解和SQL生成将失败。

3. **数据库**：启动前确保 MySQL 服务已运行，`eastmoney_db` 数据库和 `etf_option_data` 表已创建。

4. **爬虫限制**：东方财富有反爬机制，`/api/crawl_50etf` 接口可能因请求频率限制而失败，这属于正常情况。

5. **查询超时**：LLM 调用（规范化 + SQL生成）需要网络请求，单次 `/api/query` 调用可能需要 3~10 秒，前端建议设置 30 秒超时并添加 loading 状态。

6. **安全性**：`.env` 文件包含敏感信息（API密钥、数据库密码），已通过 `.gitignore` 排除，请勿手动提交到版本库。

7. **仅支持 SELECT**：`run_query()` 仅允许执行 `SELECT` 语句，拒绝任何写入操作，保障数据安全。

---

## 许可证

本项目为毕业设计项目，仅供学习和研究使用。
