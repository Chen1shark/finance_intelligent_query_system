import json
import os
import random
import re
import time
import urllib.parse
from datetime import datetime

import pymysql
from fastapi import HTTPException

from src.core.config import get_settings
from src.core.database import get_db_connection
from src.utils.data_parser import safe_decimal, safe_int

# 禁用代理
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(k, None)
os.environ["no_proxy"] = "*"
os.environ["NO_PROXY"] = "*"


class CrawlerService:
    """负责抓取东方财富 50ETF 期权数据并落库。"""

    @staticmethod
    def fetch_option_data():
        """抓取东方财富 50ETF 期权列表并转换为结构化数据。

        Returns:
            list[dict]: 标准化后的期权数据列表。

        Raises:
            HTTPException: 当远程抓取连续失败或未获取到有效数据时抛出。
        """
        from DrissionPage import ChromiumPage, ChromiumOptions

        settings = get_settings()
        all_processed_list = []
        page = 1
        max_pages = 10

        # 启动无头浏览器（复用实例）
        co = ChromiumOptions()
        co.headless(True)  # 无头模式
        co.no_imgs(True)   # 不加载图片，加快速度
        browser = ChromiumPage(addr_or_opts=co)

        try:
            # 监听目标域名
            domain = settings.target_url.split('/')[2]
            browser.listen.start(domain)

            while page <= max_pages:
                data = None
                for attempt in range(3):
                    try:
                        # 每次请求都动态生成时间戳和 callback，避免缓存命中。
                        timestamp = str(int(time.time() * 1000))
                        callback = f"jQuery{random.randint(1000000000, 9999999999)}_{timestamp}"
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
                            "wbp2u": "|0|0|0|web",
                            "_": timestamp,
                        }

                        delay = random.uniform(2.0, 4.0)
                        if attempt > 0:
                            delay += random.uniform(2.0, 4.0)
                        print(f"抓取第 {page} 页，第 {attempt + 1} 次请求，延迟 {delay:.2f} 秒")
                        time.sleep(delay)

                        # 构建完整 URL。
                        query_string = urllib.parse.urlencode(params)
                        full_url = f"{settings.target_url}?{query_string}"

                        # 清空监听队列，避免捕获之前的响应。
                        try:
                            while browser.listen.wait(timeout=0.1):
                                pass
                        except:
                            pass

                        # 访问 URL。
                        browser.get(full_url)

                        # 等待响应，并通过 callback 确认是当前请求的响应。
                        content = None
                        for _ in range(10):
                            pkt = browser.listen.wait()
                            if pkt and pkt.response and pkt.response.body:
                                body = pkt.response.body
                                # 兼容普通文本和压缩字节流两种响应体。
                                if isinstance(body, bytes):
                                    try:
                                        content = body.decode('utf-8')
                                    except UnicodeDecodeError:
                                        import gzip
                                        try:
                                            content = gzip.decompress(body).decode('utf-8')
                                        except:
                                            content = body.decode('utf-8', errors='ignore')
                                else:
                                    content = body
                                if content and callback in content:
                                    break
                                content = None
                            time.sleep(0.5)

                        if not content:
                            raise ConnectionError("未获取到响应数据")

                        match = re.search(r"^jQuery\d+_\d+\((.*)\);?$", content)
                        if not match:
                            raise ValueError("返回结果不是有效的 JSONP 数据")

                        data = json.loads(match.group(1))
                        break
                    except (ConnectionError, ValueError, json.JSONDecodeError) as exc:
                        if attempt == 2:
                            raise HTTPException(status_code=502, detail=f"期权数据抓取失败: {exc}") from exc
                        print(f"第 {attempt + 1} 次请求失败，准备重试: {exc}")
                        time.sleep(random.uniform(1.0, 2.0))

                if not data or not (data.get("data") or {}).get("diff"):
                    print(f"第 {page} 页无数据，结束抓取")
                    break

                for item in data["data"]["diff"]:
                    all_processed_list.append(
                        {
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
                            "etf_type": "50ETF",
                        }
                    )

                page += 1

            if not all_processed_list:
                raise HTTPException(status_code=502, detail="未抓取到 50ETF 期权数据")

            return all_processed_list
        finally:
            # 无论成功与否都关闭浏览器资源，避免后台进程泄漏。
            browser.listen.stop()
            browser.quit()

    @staticmethod
    def save_data_to_db(data_list):
        """将抓取结果写入数据库表。

        Args:
            data_list: 抓取并标准化后的期权数据列表。

        Returns:
            int: 本次执行影响的数据库记录数；空数据直接返回 ``0``。

        Raises:
            HTTPException: 当数据库写入失败时抛出 500 异常。
        """
        if not data_list:
            return 0

        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE etf_option_data;")
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
                insert_data = [
                    (
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
                        item["etf_type"],
                    )
                    for item in data_list
                ]
                cursor.executemany(sql, insert_data)
                connection.commit()
                return cursor.rowcount
        except pymysql.MySQLError as exc:
            if connection:
                connection.rollback()
            raise HTTPException(status_code=500, detail=f"数据库操作失败: {exc}") from exc
        finally:
            if connection:
                connection.close()
