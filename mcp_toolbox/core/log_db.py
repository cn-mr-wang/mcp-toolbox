"""Call log database layer — schema and CRUD."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from mcp_toolbox.core.database import Database

_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,     -- 自增主键
    tool_name TEXT NOT NULL,                   -- 工具名称
    tool_type TEXT NOT NULL,                   -- 工具类型（python/shell/java/sql）
    input_params TEXT NOT NULL,                -- 输入参数（JSON 字符串）
    output TEXT,                               -- 输出结果（JSON 字符串，可为空）
    duration_ms REAL NOT NULL,                 -- 执行耗时（毫秒）
    status TEXT NOT NULL,                      -- 执行状态（success/error）
    error_message TEXT,                        -- 错误信息（成功时为空）
    error_category TEXT,                       -- 错误分类（timeout/connection/permission 等）
    timestamp TEXT NOT NULL                    -- 调用时间（ISO 8601 UTC）
);
"""

_SCHEMA_MYSQL = """
CREATE TABLE IF NOT EXISTS call_logs (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    tool_name VARCHAR(255) NOT NULL COMMENT '工具名称',
    tool_type VARCHAR(50) NOT NULL COMMENT '工具类型（python/shell/java/sql）',
    input_params TEXT NOT NULL COMMENT '输入参数（JSON 字符串）',
    output TEXT COMMENT '输出结果（JSON 字符串，可为空）',
    duration_ms DOUBLE NOT NULL COMMENT '执行耗时（毫秒）',
    status VARCHAR(20) NOT NULL COMMENT '执行状态（success/error）',
    error_message TEXT COMMENT '错误信息（成功时为空）',
    error_category VARCHAR(50) COMMENT '错误分类（timeout/connection/permission 等）',
    timestamp VARCHAR(64) NOT NULL COMMENT '调用时间（ISO 8601 UTC）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工具调用日志表';
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_call_logs_tool_name ON call_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_call_logs_timestamp ON call_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_call_logs_status ON call_logs(status);
"""

_INDEXES_MYSQL = """
CREATE INDEX IF NOT EXISTS idx_call_logs_tool_name ON call_logs(tool_name(100));
CREATE INDEX IF NOT EXISTS idx_call_logs_timestamp ON call_logs(timestamp(64));
CREATE INDEX IF NOT EXISTS idx_call_logs_status ON call_logs(status(20));
"""


class LogDB:
    """Store for tool call logs."""

    def __init__(self, db: Database, retention_days: int = 7):
        self.db = db
        self.retention_days = max(1, retention_days)
        self._init_db()

    def _init_db(self):
        if self.db.dialect == "mysql":
            self.db.executescript(_SCHEMA_MYSQL)
            try:
                self.db.executescript(_INDEXES_MYSQL)
            except Exception:
                pass  # indexes may already exist
        else:
            self.db.executescript(_SCHEMA_SQLITE + _INDEXES)
        # Migration: add error_category column if missing
        if not self.db.column_exists("call_logs", "error_category"):
            try:
                self.db.execute("ALTER TABLE call_logs ADD COLUMN error_category TEXT")
            except Exception:
                pass

    def cleanup_old_logs(self) -> int:
        """Delete logs older than retention_days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        row = self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM call_logs WHERE timestamp < ?", (cutoff,)
        )
        count = row["cnt"] if row else 0
        if count > 0:
            self.db.execute("DELETE FROM call_logs WHERE timestamp < ?", (cutoff,))
        return count

    def log_call(
        self,
        tool_name: str,
        tool_type: str,
        input_params: dict,
        output: Any,
        duration_ms: float,
        status: str,
        error_message: Optional[str] = None,
        error_category: Optional[str] = None,
    ):
        """Record a tool call."""
        if isinstance(output, str):
            output_str = output
        elif output is None:
            output_str = None
        else:
            output_str = json.dumps(output, ensure_ascii=False, default=str)

        self.db.execute(
            """INSERT INTO call_logs
               (tool_name, tool_type, input_params, output, duration_ms,
                status, error_message, error_category, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tool_name,
                tool_type,
                json.dumps(input_params, ensure_ascii=False, default=str),
                output_str,
                duration_ms,
                status,
                error_message,
                error_category,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def get_logs(
        self,
        tool_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """Get call logs with optional filters."""
        conditions = []
        params = []

        if tool_name:
            conditions.append("tool_name = ?")
            params.append(tool_name)
        if status:
            conditions.append("status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT id, tool_name, tool_type, input_params, output,
                   duration_ms, status, error_message, error_category, timestamp
            FROM call_logs
            {where}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = self.db.fetchall(query, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    def get_log_by_id(self, log_id: int) -> Optional[dict]:
        """Get a single log entry by ID."""
        row = self.db.fetchone("SELECT * FROM call_logs WHERE id = ?", (log_id,))
        return self._row_to_dict(row) if row else None

    def get_stats(self) -> dict:
        """Get summary statistics."""
        total = self.db.fetchone("SELECT COUNT(*) as c FROM call_logs")["c"]
        success = self.db.fetchone(
            "SELECT COUNT(*) as c FROM call_logs WHERE status = 'success'"
        )["c"]
        error = total - success

        avg_row = self.db.fetchone("SELECT AVG(duration_ms) as avg_ms FROM call_logs")
        avg_duration = round(avg_row["avg_ms"] or 0, 2)

        tool_rows = self.db.fetchall(
            """SELECT tool_name, tool_type, COUNT(*) as calls,
                      SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success_count,
                      AVG(duration_ms) as avg_ms
               FROM call_logs GROUP BY tool_name ORDER BY calls DESC"""
        )

        calls_per_tool = []
        for row in tool_rows:
            calls_per_tool.append({
                "tool_name": row["tool_name"],
                "tool_type": row["tool_type"],
                "calls": row["calls"],
                "success_count": row["success_count"],
                "error_count": row["calls"] - row["success_count"],
                "avg_duration_ms": round(row["avg_ms"] or 0, 2),
            })

        return {
            "total_calls": total,
            "success_count": success,
            "error_count": error,
            "success_rate": round(success / total * 100, 1) if total > 0 else 0,
            "avg_duration_ms": avg_duration,
            "calls_per_tool": calls_per_tool,
        }

    def get_tool_stats(self, tool_name: str) -> dict:
        """Get stats for a specific tool."""
        row = self.db.fetchone(
            """SELECT COUNT(*) as total,
                      SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success,
                      AVG(duration_ms) as avg_ms,
                      MIN(duration_ms) as min_ms,
                      MAX(duration_ms) as max_ms
               FROM call_logs WHERE tool_name = ?""",
            (tool_name,),
        )

        if not row or row["total"] == 0:
            return {
                "tool_name": tool_name,
                "total_calls": 0,
                "success_count": 0,
                "error_count": 0,
                "success_rate": 0,
                "avg_duration_ms": 0,
                "min_duration_ms": 0,
                "max_duration_ms": 0,
            }

        return {
            "tool_name": tool_name,
            "total_calls": row["total"],
            "success_count": row["success"],
            "error_count": row["total"] - row["success"],
            "success_rate": round(row["success"] / row["total"] * 100, 1),
            "avg_duration_ms": round(row["avg_ms"] or 0, 2),
            "min_duration_ms": round(row["min_ms"] or 0, 2),
            "max_duration_ms": round(row["max_ms"] or 0, 2),
        }

    @staticmethod
    def _row_to_dict(row: dict) -> dict:
        """Parse JSON fields in a row dict."""
        d = dict(row)
        for field in ("input_params", "output"):
            if d.get(field) and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
