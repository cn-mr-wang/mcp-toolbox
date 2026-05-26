"""MySQL database adapter."""

from typing import List, Optional

from mcp_toolbox.core.database import Database


class MySQLAdapter(Database):
    """MySQL implementation of the Database interface using pymysql."""

    def __init__(self, host: str = "localhost", port: int = 3306,
                 user: str = "root", password: str = "", database: str = "mcp_toolbox"):
        try:
            import pymysql
        except ImportError:
            raise ImportError(
                "pymysql is not installed. Run: pip install mcp-toolbox[mysql]"
            )
        self._pymysql = pymysql
        self._conn_kwargs = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
            "autocommit": True,
        }
        self._conn = None

    @property
    def dialect(self) -> str:
        return "mysql"

    def _get_conn(self):
        if self._conn is None or not self._conn.open:
            self._conn = self._pymysql.connect(**self._conn_kwargs)
        return self._conn

    @staticmethod
    def _convert_sql(sql: str) -> str:
        """Convert ? placeholders to %s for pymysql."""
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: tuple = ()):
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(self._convert_sql(sql), params)

    def execute_returning_id(self, sql: str, params: tuple = ()) -> int:
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(self._convert_sql(sql), params)
            return cursor.lastrowid

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[dict]:
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(self._convert_sql(sql), params)
            return cursor.fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> List[dict]:
        conn = self._get_conn()
        with conn.cursor() as cursor:
            cursor.execute(self._convert_sql(sql), params)
            return cursor.fetchall()

    def executescript(self, script: str):
        conn = self._get_conn()
        with conn.cursor() as cursor:
            for statement in script.split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)

    def table_exists(self, table_name: str) -> bool:
        row = self.fetchone(
            "SELECT TABLE_NAME as name FROM information_schema.tables "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
            (table_name,),
        )
        return row is not None

    def column_exists(self, table_name: str, column_name: str) -> bool:
        row = self.fetchone(
            "SELECT COLUMN_NAME as name FROM information_schema.columns "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
            (table_name, column_name),
        )
        return row is not None

    def close(self):
        if self._conn and self._conn.open:
            self._conn.close()
            self._conn = None
