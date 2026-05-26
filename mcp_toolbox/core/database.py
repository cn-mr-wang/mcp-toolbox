"""Database abstraction layer — interface and factory."""

from abc import ABC, abstractmethod
from typing import List, Optional


class Database(ABC):
    """Abstract database interface for SQLite and MySQL."""

    @property
    @abstractmethod
    def dialect(self) -> str:
        """Return 'sqlite' or 'mysql'."""

    @abstractmethod
    def execute(self, sql: str, params: tuple = ()):
        """Execute INSERT/UPDATE/DELETE/DDL."""

    @abstractmethod
    def execute_returning_id(self, sql: str, params: tuple = ()) -> int:
        """Execute INSERT and return the auto-increment ID."""

    @abstractmethod
    def fetchone(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """Fetch a single row as dict."""

    @abstractmethod
    def fetchall(self, sql: str, params: tuple = ()) -> List[dict]:
        """Fetch all rows as list of dicts."""

    @abstractmethod
    def executescript(self, script: str):
        """Execute multiple SQL statements (for schema creation)."""

    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""

    @abstractmethod
    def column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""

    @abstractmethod
    def close(self):
        """Close the database connection."""


def create_database(db_type: str, **kwargs) -> Database:
    """Create a database instance.

    Args:
        db_type: "sqlite" or "mysql"
        **kwargs: SQLite needs db_path; MySQL needs host/port/user/password/database
    """
    if db_type == "sqlite":
        from mcp_toolbox.core.sqlite_adapter import SQLiteAdapter
        return SQLiteAdapter(db_path=kwargs.get("db_path", "mcp_toolbox.db"))
    elif db_type == "mysql":
        from mcp_toolbox.core.mysql_adapter import MySQLAdapter
        return MySQLAdapter(
            host=kwargs.get("host", "localhost"),
            port=kwargs.get("port", 3306),
            user=kwargs.get("user", "root"),
            password=kwargs.get("password", ""),
            database=kwargs.get("database", "mcp_toolbox"),
        )
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
