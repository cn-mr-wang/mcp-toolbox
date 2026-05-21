"""Call log data access layer using SQLite."""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from mcp_toolbox.logging.models import CALL_LOGS_SCHEMA, TOKENS_SCHEMA, _MIGRATE_ERROR_CATEGORY


class CallLogStore:
    """SQLite-backed store for tool call logs."""

    def __init__(self, db_path: str = "mcp_toolbox.db", retention_days: int = 7):
        self.db_path = db_path
        self.retention_days = max(1, retention_days)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(CALL_LOGS_SCHEMA)
            conn.executescript(TOKENS_SCHEMA)
            # Migration: add error_category column if missing
            try:
                conn.execute(_MIGRATE_ERROR_CATEGORY)
            except sqlite3.OperationalError:
                pass  # column already exists

    def cleanup_old_logs(self) -> int:
        """Delete logs older than retention_days.

        Returns:
            Number of deleted log entries.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM call_logs WHERE timestamp < ?", (cutoff,)
            )
            deleted = cursor.rowcount
            conn.commit()
        # VACUUM must be outside a transaction
        if deleted > 0:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("VACUUM")
        return deleted

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
        # Serialize output
        if isinstance(output, str):
            output_str = output
        elif output is None:
            output_str = None
        else:
            output_str = json.dumps(output, ensure_ascii=False, default=str)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
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

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_log_by_id(self, log_id: int) -> Optional[dict]:
        """Get a single log entry by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM call_logs WHERE id = ?", (log_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_stats(self) -> dict:
        """Get summary statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Total counts
            total = conn.execute("SELECT COUNT(*) as c FROM call_logs").fetchone()["c"]
            success = conn.execute(
                "SELECT COUNT(*) as c FROM call_logs WHERE status = 'success'"
            ).fetchone()["c"]
            error = total - success

            # Average duration
            avg_row = conn.execute(
                "SELECT AVG(duration_ms) as avg_ms FROM call_logs"
            ).fetchone()
            avg_duration = round(avg_row["avg_ms"] or 0, 2)

            # Calls per tool
            tool_rows = conn.execute(
                """SELECT tool_name, tool_type, COUNT(*) as calls,
                          SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success_count,
                          AVG(duration_ms) as avg_ms
                   FROM call_logs GROUP BY tool_name ORDER BY calls DESC"""
            ).fetchall()

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
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """SELECT COUNT(*) as total,
                          SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success,
                          AVG(duration_ms) as avg_ms,
                          MIN(duration_ms) as min_ms,
                          MAX(duration_ms) as max_ms
                   FROM call_logs WHERE tool_name = ?""",
                (tool_name,),
            ).fetchone()

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
    def _row_to_dict(row) -> dict:
        """Convert a sqlite3.Row to a dict, parsing JSON fields."""
        d = dict(row)
        # Parse JSON fields
        for field in ("input_params", "output"):
            if d.get(field) and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d

    # ── Token CRUD ──────────────────────────────────────────────────

    def create_token(self, name: str, token: str, allowed_tools: Optional[list] = None) -> dict:
        """Create a new token.

        Args:
            name: Human-readable name
            token: The token string
            allowed_tools: List of tool names, or None for all tools
        """
        tools_json = json.dumps(allowed_tools) if allowed_tools is not None else None
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """INSERT INTO tokens (name, token, allowed_tools, enabled, created_at)
                   VALUES (?, ?, ?, 1, ?)""",
                (name, token, tools_json, now),
            )
            row = conn.execute(
                "SELECT * FROM tokens WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return self._token_row_to_dict(row)

    def get_tokens(self) -> list:
        """Get all tokens."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tokens ORDER BY created_at DESC"
            ).fetchall()
        return [self._token_row_to_dict(row) for row in rows]

    def get_token_by_value(self, token: str) -> Optional[dict]:
        """Get a token by its value."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM tokens WHERE token = ?", (token,)
            ).fetchone()
        return self._token_row_to_dict(row) if row else None

    def update_token(self, token_id: int, **kwargs) -> Optional[dict]:
        """Update a token's fields (name, allowed_tools, enabled)."""
        allowed = {"name", "allowed_tools", "enabled"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get_token_by_id(token_id)

        # Serialize allowed_tools to JSON
        if "allowed_tools" in updates:
            updates["allowed_tools"] = (
                json.dumps(updates["allowed_tools"])
                if updates["allowed_tools"] is not None
                else None
            )

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [token_id]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE tokens SET {set_clause} WHERE id = ?", values
            )
        return self.get_token_by_id(token_id)

    def delete_token(self, token_id: int) -> bool:
        """Delete a token. Returns True if deleted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM tokens WHERE id = ?", (token_id,))
            return cursor.rowcount > 0

    def get_token_by_id(self, token_id: int) -> Optional[dict]:
        """Get a token by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM tokens WHERE id = ?", (token_id,)
            ).fetchone()
        return self._token_row_to_dict(row) if row else None

    @staticmethod
    def _token_row_to_dict(row) -> dict:
        """Convert a token row to dict, parsing allowed_tools JSON."""
        d = dict(row)
        if d.get("allowed_tools") and isinstance(d["allowed_tools"], str):
            try:
                d["allowed_tools"] = json.loads(d["allowed_tools"])
            except (json.JSONDecodeError, TypeError):
                pass
        d["enabled"] = bool(d.get("enabled", 1))
        return d

    def cleanup_token_tools(self, valid_tools: list) -> int:
        """Validate and normalize all tokens' allowed_tools.

        - null tokens (legacy "all tools") are expanded to explicit tool lists
        - Tokens with non-existent tools have those tools removed

        Args:
            valid_tools: List of currently loaded tool names

        Returns:
            Number of tokens that were cleaned up.
        """
        valid_set = set(valid_tools)
        tools_json = json.dumps(valid_tools)
        cleaned = 0
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, allowed_tools FROM tokens").fetchall()
            for row in rows:
                raw = row["allowed_tools"]
                if raw is None:
                    # Legacy "all tools" token → expand to explicit list
                    conn.execute(
                        "UPDATE tokens SET allowed_tools = ? WHERE id = ?",
                        (tools_json, row["id"]),
                    )
                    cleaned += 1
                else:
                    try:
                        tools = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    filtered = [t for t in tools if t in valid_set]
                    if len(filtered) != len(tools):
                        conn.execute(
                            "UPDATE tokens SET allowed_tools = ? WHERE id = ?",
                            (json.dumps(filtered), row["id"]),
                        )
                        cleaned += 1
        return cleaned
