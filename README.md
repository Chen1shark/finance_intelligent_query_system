# 50ETF 期权智能问数系统

本项目是一个面向 50ETF 期权数据的 NL2SQL 智能查询系统。用户可以输入自然语言问题，系统会完成语义规范化、核心需求提取、模板匹配、SQL 生成与数据库查询，并将结果以统一 JSON 格式返回给前端展示。

项目主要用于本科毕业设计，目标是实现一个完整、可演示、可解释的金融数据智能问答系统，而不是追求复杂的生产级平台能力。

## 功能概览

- 50ETF 期权行情数据抓取：从东方财富接口获取期权合约数据并写入 MySQL。
- 自然语言查询：支持用户用中文描述查询需求，例如“查询认购期权中最新价最高的合约”。
- NL2SQL 生成：结合规则、向量模板匹配和大语言模型生成可执行 SQL。
- 查询结果展示：返回结构化数据、结果模式和调试信息，便于前端展示和答辩说明。
- 数据刷新保护：抓取入库采用“临时表 + 事务替换”方式，避免刷新失败导致旧数据丢失。
- SQL 安全限制：数据库查询只允许执行 `SELECT`，降低 LLM 生成危险 SQL 的风险。
- 统一响应结构：接口统一返回 `{code, msg, data}`，方便前端处理。
- 日志输出：后端使用 `logging` 输出运行日志，替代零散 `print`。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 后端框架 | FastAPI, Uvicorn |
| 前端框架 | Vue 3, TypeScript, Vite |
| 图表展示 | ECharts |
| 数据库 | MySQL, PyMySQL |
| 大语言模型 | DashScope 兼容 OpenAI SDK 调用 |
| 向量检索 | FAISS, text embedding |
| 配置管理 | pydantic-settings, python-dotenv |

## 项目结构

```text
finance_intelligent_query_system/
├─ back_end/
│  ├─ data/
│  │  ├─ rules_50etf.json          # 业务规则配置
│  │  ├─ vector_store.json         # 标准问题、SQL 模板和向量数据
│  │  └─ schema/sql.sql            # 数据库表结构
│  ├─ src/
│  │  ├─ api/
│  │  │  ├─ routes.py              # API 路由
│  │  │  └─ schemas.py             # 请求模型和统一响应工具
│  │  ├─ core/
│  │  │  ├─ config.py              # 环境变量配置
│  │  │  ├─ database.py            # 数据库连接和查询执行
│  │  │  └─ llm_client.py          # LLM 客户端封装
│  │  ├─ services/
│  │  │  ├─ crawler_service.py     # 数据抓取与入库
│  │  │  ├─ semantic_service.py    # 语义规范化和核心需求提取
│  │  │  ├─ sql_service.py         # SQL 生成、校验和结果模式识别
│  │  │  └─ vector_service.py      # 向量模板匹配
│  │  ├─ utils/
│  │  │  └─ data_parser.py         # 爬虫数据类型转换工具
│  │  └─ main.py                   # FastAPI 应用入口
│  ├─ .env.example
│  └─ requirements.txt
├─ front_end/
│  ├─ src/
│  │  ├─ api/                      # 前端接口调用
│  │  ├─ components/               # 页面组件
│  │  ├─ router/                   # 路由配置
│  │  ├─ types/                    # TypeScript 类型
│  │  └─ views/                    # 页面视图
│  ├─ .env.example
│  └─ package.json
└─ README.md
```

## 核心流程

### 查询流程

```text
用户输入自然语言问题
        ↓
语义规范化：修正表达、统一金融术语
        ↓
核心需求提取：得到更短、更明确的查询意图
        ↓
向量模板匹配：从标准问题库中匹配相似 SQL 模板
        ↓
LLM 生成 SQL：结合原问题、核心需求和模板生成 SQL
        ↓
SQL 安全校验：只允许 SELECT 查询
        ↓
MySQL 查询：返回结构化结果
```

### 数据刷新流程

```text
抓取东方财富期权数据
        ↓
写入临时表 tmp_etf_option_data
        ↓
校验临时表记录数
        ↓
开启事务
        ↓
DELETE 正式表旧数据
        ↓
INSERT SELECT 从临时表回填正式表
        ↓
校验正式表记录数
        ↓
COMMIT 或 ROLLBACK
```

这种方式避免了直接 `TRUNCATE` 正式表带来的风险。如果刷新过程中出错，事务可以回滚，旧数据不会被破坏。

## 环境要求

- Python 3.8+
- Node.js 18+
- MySQL 8.0+
- 可用的 DashScope API Key

## 后端启动

进入后端目录：

```powershell
cd back_end
```

安装依赖：

```powershell
pip install -r requirements.txt
```

复制环境变量模板：

```powershell
copy .env.example .env
```

编辑 `back_end/.env`，至少需要配置：

```env
API_KEY=your-api-key-here
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password-here
DB_NAME=eastmoney_db
```

初始化数据库：

```sql
CREATE DATABASE IF NOT EXISTS eastmoney_db DEFAULT CHARSET utf8mb4;
```

然后在 `back_end` 目录下执行：

```powershell
mysql -u root -p eastmoney_db < data\schema\sql.sql
```

启动后端服务：

```powershell
python -m src.main
```

后端默认地址：

- API 服务：`http://127.0.0.1:8000`
- Swagger 文档：`http://127.0.0.1:8000/docs`
- ReDoc 文档：`http://127.0.0.1:8000/redoc`

## 前端启动

进入前端目录：

```powershell
cd front_end
```

安装依赖：

```powershell
npm install
```

复制环境变量模板：

```powershell
copy .env.example .env
```

确认 `front_end/.env` 中的接口地址：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

启动前端：

```powershell
npm run dev
```

## API 说明

后端统一使用 `/api` 前缀。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/crawl_50etf` | 抓取并刷新 50ETF 期权数据 |
| GET | `/api/data_status` | 查看当前数据库中的数据状态 |
| POST | `/api/normalize` | 对用户问题进行语义规范化 |
| POST | `/api/extract_core` | 提取用户问题的核心查询需求 |
| POST | `/api/match` | 匹配最相似的标准问题和 SQL 模板 |
| POST | `/api/query` | 生成 SQL 并查询数据库 |
| POST | `/api/query_debug` | 查询并返回各阶段耗时和调试信息 |

POST 接口请求体示例：

```json
{
  "text": "查询认购期权中最新价最高的前十个合约"
}
```

统一响应结构：

```json
{
  "code": 200,
  "msg": "处理成功",
  "data": {}
}
```

`/api/query` 响应中的主要字段：

| 字段 | 说明 |
| --- | --- |
| `normalized_text` | 规范化后的用户问题 |
| `core_need` | 提取后的核心查询需求 |
| `sql` | 最终执行的 SQL |
| `rows` | 查询结果列表 |
| `total` | 查询结果数量 |
| `result_mode` | 前端展示模式标识 |

## 数据表说明

核心业务表为 `etf_option_data`，用于保存当前批次的 50ETF 期权合约行情数据。

主要字段：

| 字段 | 说明 |
| --- | --- |
| `contract_code` | 合约代码 |
| `contract_name` | 合约名称 |
| `latest_price` | 最新价 |
| `price_change` | 涨跌额 |
| `price_change_rate` | 涨跌幅 |
| `volume` | 成交量 |
| `turnover` | 成交额 |
| `position_volume` | 持仓量 |
| `strike_price` | 行权价 |
| `remain_days` | 剩余天数 |
| `position_change` | 持仓量日增 |
| `settlement_price_yesterday` | 昨日结算价 |
| `open_price_today` | 今日开盘价 |
| `etf_type` | 期权类型标识 |
| `create_time` | 数据入库时间 |

## 适合答辩说明的优化点

- 数据刷新安全：不再先清空正式表，而是先写临时表，成功后用事务替换正式表。
- SQL 执行安全：只允许执行 `SELECT` 查询，避免模型生成写入、删除、修改类 SQL。
- 响应结构统一：所有正常接口返回统一 `{code, msg, data}`，前后端约定更清晰。
- 日志规范化：使用 `logging` 记录后端运行过程，便于排查接口、爬虫和模型调用问题。
- 模块拆分清楚：爬虫、语义处理、向量检索、SQL 生成、数据库执行分别封装，便于说明系统架构。

## 常见问题

### 1. 启动时报 `API_KEY` 为空

检查 `back_end/.env` 是否存在，并确认 `API_KEY` 已填写。

### 2. 数据库连接失败

检查 MySQL 是否启动，以及 `DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME` 是否正确。

### 3. 查询没有数据

先调用 `/api/crawl_50etf` 抓取数据，再调用 `/api/data_status` 确认正式表中已有记录。

### 4. 前端请求失败

确认后端服务运行在 `http://127.0.0.1:8000`，并检查 `front_end/.env` 中的 `VITE_API_BASE_URL` 是否一致。

