"""SQL tool executor - executes SQL queries against databases."""

import re
import threading
import time
from urllib.parse import urlparse

from mcp_toolbox.core.errors import ErrorCategory, format_error
from mcp_toolbox.core.types import ToolEntry, ToolResult
from mcp_toolbox.executors.base import BaseExecutor
from mcp_toolbox.executors.config_vars import resolve_config_vars
from mcp_toolbox.executors.shell_executor import _load_file


# Connection pool keyed by connection string
_connection_pool: dict[str, object] = {}
_pool_lock = threading.Lock()


def _create_connection(conn_str: str):
    """Create a database connection from a connection string."""
    if conn_str.startswith("sqlite"):
        import sqlite3
        parsed = urlparse(conn_str)
        path = parsed.path
        if not path:
            path = conn_str.replace("sqlite:", "").lstrip("/")
        try:
            return sqlite3.connect(path, check_same_thread=False)
        except sqlite3.DatabaseError as e:
            if "readonly" in str(e).lower() or "permission" in str(e).lower():
                raise PermissionError(f"SQLite 数据库只读或无权限: {path}") from e
            raise
    elif conn_str.startswith("postgresql"):
        try:
            import psycopg2
            return psycopg2.connect(conn_str)
        except ImportError:
            raise ImportError(
                "psycopg2 未安装，执行: pip install mcp-toolbox[postgres]"
            )
    elif conn_str.startswith("mysql"):
        try:
            import pymysql
            parsed = urlparse(conn_str)
            return pymysql.connect(
                host=parsed.hostname or "localhost",
                port=parsed.port or 3306,
                user=parsed.username or "root",
                password=parsed.password or "",
                database=parsed.path.lstrip("/"),
            )
        except ImportError:
            raise ImportError(
                "pymysql 未安装，执行: pip install mcp-toolbox[mysql]"
            )
    else:
        raise ValueError(f"不支持的数据库连接协议: {conn_str.split('://')[0]}")


def _get_connection(conn_str: str):
    """Get or create a pooled connection by connection string."""
    with _pool_lock:
        if conn_str in _connection_pool:
            conn = _connection_pool[conn_str]
            # Verify connection is still alive
            try:
                if hasattr(conn, "ping"):
                    conn.ping(reconnect=True)
                elif hasattr(conn, "execute"):
                    conn.execute("SELECT 1")
                return conn
            except Exception:
                # Connection dead, remove and recreate
                _connection_pool.pop(conn_str, None)

        conn = _create_connection(conn_str)
        _connection_pool[conn_str] = conn
        return conn


def _get_driver_prefix(conn_str: str) -> str:
    """Get driver type from connection string."""
    if conn_str.startswith("sqlite"):
        return "sqlite"
    elif conn_str.startswith("postgresql"):
        return "postgresql"
    elif conn_str.startswith("mysql"):
        return "mysql"
    return ""


def _build_query(template: str, params: dict, driver: str) -> tuple:
    """Build parameterized query safely.

    Scans for {param} placeholders and replaces them with driver-specific
    parameterized placeholders. All drivers use named parameters + dict binding.

    Returns (query, params_dict) for cursor.execute(query, params).
    """
    query = template
    query_params = {}

    for key, value in params.items():
        placeholder = f"{{{key}}}"
        if placeholder not in query:
            continue

        if driver == "sqlite":
            safe_placeholder = f":{key}"       # SQLite named param
        elif driver == "postgresql":
            safe_placeholder = f"%({key})s"    # psycopg2 named param
        elif driver == "mysql":
            safe_placeholder = f"%({key})s"    # pymysql named param
        else:
            safe_placeholder = f":{key}"

        query = query.replace(placeholder, safe_placeholder)
        query_params[key] = value

    return query, query_params if query_params else None


class SQLExecutor(BaseExecutor):
    """Executes SQL tools by connecting to databases and running queries.

    Connection string must be specified using {config:...} template variable.
    Query can be specified inline or loaded from a file.

    Supports: SQLite, PostgreSQL, MySQL.
    """

    def execute(self, entry: ToolEntry, params: dict) -> ToolResult:
        connection_ref = entry.metadata.get("connection", "")
        query_template = entry.metadata.get("query", "")
        query_file = entry.metadata.get("query_file", "")

        # Resolve {config:...} in connection string
        connection_ref = resolve_config_vars(connection_ref)

        if not connection_ref:
            return ToolResult(
                success=False, output=None,
                error="[config] 未指定 'connection' 配置\n建议: 使用 {config:name.key} 从配置项获取连接字符串",
                error_category=ErrorCategory.CONFIGURATION.value,
                duration_ms=0.0,
            )

        # Load query from file if specified
        if query_file and not query_template:
            query_template = _load_file(query_file, entry.module_name)
            if query_template is None:
                return ToolResult(
                    success=False, output=None,
                    error=f"[not_found] SQL 文件不存在: {query_file}\n建议: 检查 query_file 路径是否正确",
                    error_category=ErrorCategory.NOT_FOUND.value,
                    duration_ms=0.0,
                )

        # Resolve {config:...} in query template
        query_template = resolve_config_vars(query_template)

        if not query_template:
            return ToolResult(
                success=False, output=None,
                error="[config] 未指定 'query' 或 'query_file' 配置\n建议: 在 @toolbox.tool() 中设置 query（内联SQL）或 query_file（SQL文件路径）",
                error_category=ErrorCategory.CONFIGURATION.value,
                duration_ms=0.0,
            )

        # Get pooled connection (reuses existing connection)
        try:
            conn = _get_connection(connection_ref)
        except Exception as e:
            msg, category = format_error(e, entry.name)
            return ToolResult(
                success=False, output=None, error=msg,
                error_category=category.value, duration_ms=0.0,
            )

        driver = _get_driver_prefix(connection_ref)
        query, query_params = _build_query(query_template, params, driver)

        start = time.monotonic()
        try:
            cursor = conn.cursor()
            if query_params:
                cursor.execute(query, query_params)
            else:
                cursor.execute(query)

            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                output = {
                    "columns": columns,
                    "rows": rows,
                    "count": len(rows),
                }
            else:
                conn.commit()
                output = {"affected_rows": cursor.rowcount}

            duration = (time.monotonic() - start) * 1000
            return ToolResult(success=True, output=output, duration_ms=duration)
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            msg, category = format_error(e, entry.name)
            return ToolResult(
                success=False, output=None, error=msg,
                error_category=category.value, duration_ms=duration,
            )
