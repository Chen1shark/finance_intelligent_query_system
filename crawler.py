import re
import time
import random
import requests
import json
import pymysql
from fastapi import HTTPException
import config

# 全局会话对象，复用连接和Cookie
SESSION = requests.Session()

def safe_decimal(val, divisor=1):
    """安全转换小数并按指定除数缩放，处理空值和异常"""
    if val == "-" or val is None or val == "":
        return None
    try:
        return round(float(val) / divisor, 3)
    except ValueError:
        return None

def safe_int(val):
    """安全转换整数，处理空值和异常"""
    if val == "-" or val is None or val == "":
        return None
    try:
        return int(val)
    except ValueError:
        return None

def get_db_connection():
    """创建并返回MySQL数据库连接"""
    try:
        connection = pymysql.connect(**config.DB_CONFIG)
        return connection
    except pymysql.MySQLError as e:
        print(f"数据库连接失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {str(e)}")

def fetch_option_data():
    """爬取50ETF期权数据并返回结构化列表"""
    all_processed_list = []
    page = 1
    max_pages = 10
    
    while page <= max_pages:
        # 生成动态时间戳和回调函数名
        timestamp = str(int(time.time() * 1000))
        callback = f"jQuery{random.randint(1000000000, 9999999999)}_{timestamp}"
        
        # 构造请求参数
        params = {
            "np": "1",
            "fltt": "1",
            "invt": "2",
            "cb": callback,
            "fs": "m:10+c:510050",
            "fields": "f12,f14,f2,f4,f3,f5,f6,f108,f161,f162,f163,f28,f17",
            "fid": "f3",
            "pn": str(page),
            "pz": "50",
            "po": "1",
            "dect": "1",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "_": timestamp
        }

        max_retries = 3
        data = None
        
        # 带重试机制的请求逻辑
        for attempt in range(max_retries):
            try:
                # 构造请求头，模拟浏览器访问
                headers = {
                    "User-Agent": random.choice([
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ]),
                    "Referer": "https://quote.eastmoney.com/option/510050.html",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Connection": "keep-alive",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "Host": "push2.eastmoney.com",
                    "X-Requested-With": "XMLHttpRequest"
                }
                
                # 随机延迟，避免高频请求
                delay = random.uniform(2.0, 4.0)
                if attempt > 0:
                    delay += random.uniform(1.0, 3.0)
                print(f"爬取第{page}页，第{attempt+1}次请求，延迟{delay:.2f}秒")
                time.sleep(delay)
                
                # 发送GET请求
                SESSION.headers.update(headers)
                response = SESSION.get(
                    config.TARGET_URL,
                    params=params,
                    timeout=20,
                    verify=False
                )
                response.raise_for_status()
                
                # 解析JSONP格式响应
                content = response.text.strip()
                match = re.search(r'^jQuery\d+_\d+\((.*)\);?$', content)
                if not match:
                    raise ValueError("返回数据格式不是有效的JSONP")
                    
                json_str = match.group(1)
                data = json.loads(json_str)
                break
                
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                print(f"第{attempt + 1}次请求失败，正在重试: {e}")
                time.sleep(random.uniform(1, 3))
        
        # 无数据则终止分页爬取
        if not data or not data.get("data", {}).get("diff"):
            print(f"第{page}页无数据，结束爬取")
            break
        
        # 解析原始数据并结构化
        raw_list = data["data"]["diff"]
        for item in raw_list:
            processed_item = {
                "contract_code": str(item.get("f12", "")),
                "contract_name": str(item.get("f14", "")),
                "latest_price": safe_decimal(item.get("f2"), 1000),
                "price_change": safe_decimal(item.get("f4"), 1000),
                "price_change_rate": safe_decimal(item.get("f3"), 100),
                "volume": safe_int(item.get("f5")),
                "turnover": safe_decimal(item.get("f6"), 1),
                "position_volume": safe_int(item.get("f108")),
                "strike_price": safe_decimal(item.get("f161"), 1000),
                "remain_days": safe_int(item.get("f162")),
                "position_change": safe_int(item.get("f163")),
                "settlement_price_yesterday": safe_decimal(item.get("f28"), 1000),
                "open_price_today": safe_decimal(item.get("f17"), 1000),
                "etf_type": "50ETF"
            }
            all_processed_list.append(processed_item)
        
        # 翻页
        page += 1
    
    return all_processed_list

def save_data_to_db(data_list):
    """将爬取的期权数据批量入库，返回入库条数"""
    if not data_list:
        return 0
    
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 清空数据表
            truncate_sql = "TRUNCATE TABLE etf_option_data;"
            cursor.execute(truncate_sql)
            
            # 构造入库SQL
            sql = """
                INSERT INTO etf_option_data (
                    contract_code, contract_name, latest_price, price_change,
                    price_change_rate, volume, turnover, position_volume,
                    strike_price, remain_days, position_change,
                    settlement_price_yesterday, open_price_today, etf_type,
                    create_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    contract_name = VALUES(contract_name),
                    latest_price = VALUES(latest_price),
                    price_change = VALUES(price_change),
                    price_change_rate = VALUES(price_change_rate),
                    volume = VALUES(volume),
                    turnover = VALUES(turnover),
                    position_volume = VALUES(position_volume),
                    strike_price = VALUES(strike_price),
                    remain_days = VALUES(remain_days),
                    position_change = VALUES(position_change),
                    settlement_price_yesterday = VALUES(settlement_price_yesterday),
                    open_price_today = VALUES(open_price_today),
                    create_time = NOW()
            """
            
            # 组装入库数据
            insert_data = []
            for item in data_list:
                insert_data.append((
                    item["contract_code"],
                    item["contract_name"],
                    item["latest_price"],
                    item["price_change"],
                    item["price_change_rate"],
                    item["volume"],
                    item["turnover"],
                    item["position_volume"],
                    item["strike_price"],
                    item["remain_days"],
                    item["position_change"],
                    item["settlement_price_yesterday"],
                    item["open_price_today"],
                    item["etf_type"]
                ))
            
            # 批量插入数据
            cursor.executemany(sql, insert_data)
            connection.commit()
            return cursor.rowcount
    except pymysql.MySQLError as e:
        if connection:
            connection.rollback()
        print(f"数据库操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据库操作失败: {str(e)}")
    finally:
        if connection:
            connection.close() 
