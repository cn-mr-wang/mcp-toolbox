"""SQLite database adapter."""

import sqlite3
from typing import List, Optional

from mcp_toolbox.core.database import Database


class SQLiteAdapter(Database):
    """SQLite implementation of the Database interface."""

    def __init__(self, db_path: str = "mcp_toolbox.db"):
        self.db_path = db_path
        self._conn = None

    @property
    def dialect(self) -> str:
        return "sqlite"

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def execute(self, sql: str, params: tuple = ()):
        conn = self._get_conn()
        conn.execute(sql, params)
        conn.commit()

    def execute_returning_id(self, sql: str, params: tuple = ()) -> int:
        conn = self._get_conn()
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.lastrowid

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> List[dict]:
        conn = self._get_conn()
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def executescript(self, script: str):
        conn = self._get_conn()
        conn.executescript(script)

    def table_exists(self, table_name: str) -> bool:
        row = self.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return row is not None

    def column_exists(self, table_name: str, column_name: str) -> bool:
        rows = self.fetchall(f"PRAGMA table_info('{table_name}')")
        return any(row["name"] == column_name for row in rows)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
