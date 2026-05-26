"""Token database layer — schema and CRUD."""

import json
from datetime import datetime, timezone
from typing import Optional

from mcp_toolbox.core.database import Database

_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,     -- 自增主键
    name TEXT NOT NULL,                        -- Token 名称（如 dev-agent）
    token TEXT NOT NULL UNIQUE,                -- Token 值（唯一）
    allowed_tools TEXT,                        -- 允许的工具列表（JSON 数组，null=全部）
    enabled INTEGER DEFAULT 1,                 -- 是否启用（1=启用，0=禁用）
    created_at TEXT NOT NULL                   -- 创建时间（ISO 8601 UTC）
);
"""

_SCHEMA_MYSQL = """
CREATE TABLE IF NOT EXISTS tokens (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    name VARCHAR(255) NOT NULL COMMENT 'Token 名称（如 dev-agent）',
    token VARCHAR(255) NOT NULL UNIQUE COMMENT 'Token 值（唯一）',
    allowed_tools TEXT COMMENT '允许的工具列表（JSON 数组，null=全部）',
    enabled TINYINT DEFAULT 1 COMMENT '是否启用（1=启用，0=禁用）',
    created_at VARCHAR(64) NOT NULL COMMENT '创建时间（ISO 8601 UTC）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='访问控制 Token 表';
"""


class TokenDB:
    """Store for access tokens."""

    def __init__(self, db: Database):
        self.db = db
        schema = _SCHEMA_MYSQL if self.db.dialect == "mysql" else _SCHEMA_SQLITE
        self.db.executescript(schema)

    def create(self, name: str, token: str, allowed_tools: Optional[list] = None) -> dict:
        """Create a new token."""
        tools_json = json.dumps(allowed_tools) if allowed_tools is not None else None
        now = datetime.now(timezone.utc).isoformat()
        token_id = self.db.execute_returning_id(
            """INSERT INTO tokens (name, token, allowed_tools, enabled, created_at)
               VALUES (?, ?, ?, 1, ?)""",
            (name, token, tools_json, now),
        )
        return self.get_by_id(token_id)

    def get_all(self) -> list:
        """Get all tokens."""
        rows = self.db.fetchall("SELECT * FROM tokens ORDER BY created_at DESC")
        return [self._row_to_dict(row) for row in rows]

    def get_by_id(self, token_id: int) -> Optional[dict]:
        """Get a token by ID."""
        row = self.db.fetchone("SELECT * FROM tokens WHERE id = ?", (token_id,))
        return self._row_to_dict(row) if row else None

    def get_by_value(self, token: str) -> Optional[dict]:
        """Get a token by its value."""
        row = self.db.fetchone("SELECT * FROM tokens WHERE token = ?", (token,))
        return self._row_to_dict(row) if row else None

    def update(self, token_id: int, **kwargs) -> Optional[dict]:
        """Update a token's fields (name, allowed_tools, enabled)."""
        allowed = {"name", "allowed_tools", "enabled"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get_by_id(token_id)

        if "allowed_tools" in updates:
            updates["allowed_tools"] = (
                json.dumps(updates["allowed_tools"])
                if updates["allowed_tools"] is not None
                else None
            )

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [token_id]
        self.db.execute(f"UPDATE tokens SET {set_clause} WHERE id = ?", tuple(values))
        return self.get_by_id(token_id)

    def delete(self, token_id: int) -> bool:
        """Delete a token."""
        self.db.execute("DELETE FROM tokens WHERE id = ?", (token_id,))
        # Check if deleted by fetching first
        return self.get_by_id(token_id) is None

    def cleanup_tools(self, valid_tools: list) -> int:
        """Validate and normalize all tokens' allowed_tools."""
        valid_set = set(valid_tools)
        tools_json = json.dumps(valid_tools)
        cleaned = 0
        rows = self.db.fetchall("SELECT id, allowed_tools FROM tokens")
        for row in rows:
            raw = row["allowed_tools"]
            if raw is None:
                self.db.execute(
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
                    self.db.execute(
                        "UPDATE tokens SET allowed_tools = ? WHERE id = ?",
                        (json.dumps(filtered), row["id"]),
                    )
                    cleaned += 1
        return cleaned

    @staticmethod
    def _row_to_dict(row: dict) -> dict:
        """Convert a token row to dict, parsing allowed_tools JSON."""
        d = dict(row)
        if d.get("allowed_tools") and isinstance(d["allowed_tools"], str):
            try:
                d["allowed_tools"] = json.loads(d["allowed_tools"])
            except (json.JSONDecodeError, TypeError):
                pass
        d["enabled"] = bool(d.get("enabled", 1))
        return d
