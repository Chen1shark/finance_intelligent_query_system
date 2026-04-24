import json
import logging
import os
import random
import re
import time
import urllib.parse

import pymysql
from fastapi import HTTPException

from src.core.config import get_settings
from src.core.database import get_db_connection
from src.utils.data_parser import safe_decimal, safe_int

logger = logging.getLogger(__name__)

# Disable proxy variables for the Eastmoney crawler.
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(k, None)
os.environ["no_proxy"] = "*"
os.environ["NO_PROXY"] = "*"


class CrawlerService:
    """Fetch and persist 50ETF option data from Eastmoney."""

    @staticmethod
    def fetch_option_data():
        """Fetch 50ETF option data and convert it to normalized records."""
        from DrissionPage import ChromiumOptions, ChromiumPage

        settings = get_settings()
        all_processed_list = []
        page = 1
        max_pages = 10
        browser = None

        co = ChromiumOptions()
        co.headless(True)
        co.no_imgs(True)
        browser = ChromiumPage(addr_or_opts=co)

        try:
            domain = settings.target_url.split("/")[2]
            browser.listen.start(domain)

            while page <= max_pages:
                data = None
                for attempt in range(3):
                    try:
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
                        logger.info("Fetching page %s, attempt %s, delay %.2fs", page, attempt + 1, delay)
                        time.sleep(delay)

                        query_string = urllib.parse.urlencode(params)
                        full_url = f"{settings.target_url}?{query_string}"

                        try:
                            while browser.listen.wait(timeout=0.1):
                                pass
                        except Exception:
                            pass

                        browser.get(full_url)

                        content = None
                        for _ in range(10):
                            pkt = browser.listen.wait()
                            if pkt and pkt.response and pkt.response.body:
                                body = pkt.response.body
                                if isinstance(body, bytes):
                                    try:
                                        content = body.decode("utf-8")
                                    except UnicodeDecodeError:
                                        import gzip

                                        try:
                                            content = gzip.decompress(body).decode("utf-8")
                                        except Exception:
                                            content = body.decode("utf-8", errors="ignore")
                                else:
                                    content = body

                                if content and callback in content:
                                    break
                                content = None
                            time.sleep(0.5)

                        if not content:
                            raise ConnectionError("No response data received")

                        match = re.search(r"^jQuery\d+_\d+\((.*)\);?$", content)
                        if not match:
                            raise ValueError("Response is not valid JSONP")

                        data = json.loads(match.group(1))
                        break
                    except (ConnectionError, ValueError, json.JSONDecodeError) as exc:
                        if attempt == 2:
                            raise HTTPException(status_code=502, detail=f"Option data fetch failed: {exc}") from exc
                        logger.warning("Fetch attempt %s failed, retrying: %s", attempt + 1, exc)
                        time.sleep(random.uniform(1.0, 2.0))

                if not data or not (data.get("data") or {}).get("diff"):
                    logger.info("Page %s has no data, stop fetching", page)
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
                raise HTTPException(status_code=502, detail="No 50ETF option data fetched")

            return all_processed_list
        finally:
            if browser is not None:
                browser.listen.stop()
                browser.quit()

    @staticmethod
    def save_data_to_db(data_list):
        """Write new data to a temp table, then replace the formal table after validation."""
        if not data_list:
            return 0

        connection = None
        temp_table_name = "tmp_etf_option_data"
        insert_columns = (
            "contract_code",
            "contract_name",
            "latest_price",
            "price_change",
            "price_change_rate",
            "volume",
            "turnover",
            "position_volume",
            "strike_price",
            "remain_days",
            "position_change",
            "settlement_price_yesterday",
            "open_price_today",
            "etf_type",
        )
        column_list_sql = ", ".join(insert_columns)
        value_placeholders_sql = ", ".join(["%s"] * len(insert_columns))
        insert_data = [tuple(item[column] for column in insert_columns) for item in data_list]

        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TEMPORARY TABLE IF EXISTS {temp_table_name}")
                cursor.execute(f"CREATE TEMPORARY TABLE {temp_table_name} LIKE etf_option_data")

                temp_insert_sql = f"""
                    INSERT INTO {temp_table_name} ({column_list_sql})
                    VALUES ({value_placeholders_sql})
                """
                cursor.executemany(temp_insert_sql, insert_data)

                cursor.execute(f"SELECT COUNT(*) AS total FROM {temp_table_name}")
                temp_count = int((cursor.fetchone() or {}).get("total") or 0)
                if temp_count != len(data_list):
                    raise HTTPException(
                        status_code=500,
                        detail=f"Temporary table validation failed: expected {len(data_list)}, got {temp_count}",
                    )

                cursor.execute("DELETE FROM etf_option_data")
                final_insert_sql = f"""
                    INSERT INTO etf_option_data ({column_list_sql}, create_time)
                    SELECT {column_list_sql}, NOW()
                    FROM {temp_table_name}
                """
                cursor.execute(final_insert_sql)

                cursor.execute("SELECT COUNT(*) AS total FROM etf_option_data")
                final_count = int((cursor.fetchone() or {}).get("total") or 0)
                if final_count != len(data_list):
                    raise HTTPException(
                        status_code=500,
                        detail=f"Formal table validation failed: expected {len(data_list)}, got {final_count}",
                    )

                connection.commit()
                return final_count
        except pymysql.MySQLError as exc:
            if connection:
                connection.rollback()
            raise HTTPException(status_code=500, detail=f"Database operation failed: {exc}") from exc
        except HTTPException:
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f"DROP TEMPORARY TABLE IF EXISTS {temp_table_name}")
                except pymysql.MySQLError:
                    pass
                connection.close()
