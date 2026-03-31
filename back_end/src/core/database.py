from contextlib import contextmanager
import pymysql
from fastapi import HTTPException
from src.core.config import get_settings


def get_db_connection():
    """创建并返回 MySQL 数据库连接。

    Returns:
        pymysql.connections.Connection: 可执行数据库操作的连接对象。

    Raises:
        HTTPException: 当数据库连接失败时抛出 500 异常。
    """
    settings = get_settings()
    try:
        connection = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        return connection
    except pymysql.MySQLError as e:
        print(f"数据库连接失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {str(e)}")


@contextmanager
def db_connection():
    """以上下文管理器方式提供数据库连接。

    Yields:
        pymysql.connections.Connection: 当前作用域内可复用的数据库连接。
    """
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def run_query(sql):
    """执行只读 SQL 查询并返回结果。

    Args:
        sql: 待执行的 SQL 语句，仅允许 ``SELECT`` 查询。

    Returns:
        list[dict]: 查询结果列表，每一行以字典形式返回。

    Raises:
        HTTPException: 当 SQL 非法或执行失败时抛出。
    """
    if not sql or not sql.strip():
        raise HTTPException(status_code=400, detail="SQL不能为空")
    sql_text = sql.strip()
    if not sql_text.lower().startswith("select"):
        raise HTTPException(status_code=400, detail="仅支持SELECT查询")
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql_text)
            return cursor.fetchall()
    except pymysql.MySQLError as e:
        raise HTTPException(status_code=500, detail=f"数据库操作失败: {str(e)}")
    finally:
        if connection:
            connection.close()
