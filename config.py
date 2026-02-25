# ==============================================================================
# 项目配置
# ==============================================================================
import pymysql

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',        # 数据库账号（请根据实际情况修改）
    'password': '123456',  # 数据库密码（请根据实际情况修改）
    'database': 'eastmoney_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# 爬虫目标URL - 使用可用的历史数据端点
TARGET_URL = "https://push2his.eastmoney.com/api/qt/clist/get"

# 项目信息
PROJECT_NAME = "50ETF期权智能问数系统"
PROJECT_VERSION = "1.0.0"
API_PREFIX = "/api"

# Ollama配置
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen7b"
