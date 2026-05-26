"""Custom config database layer — schema and CRUD."""

from datetime import datetime, timezone
from typing import Optional

from mcp_toolbox.core.database import Database

_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS custom_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,     -- 自增主键
    name TEXT NOT NULL UNIQUE,                 -- 配置名称（如 email_server）
    content TEXT NOT NULL,                     -- YAML 格式的配置内容
    description TEXT,                          -- 配置说明
    created_at TEXT NOT NULL,                  -- 创建时间（ISO 8601 UTC）
    updated_at TEXT NOT NULL                   -- 更新时间（ISO 8601 UTC）
);
"""

_SCHEMA_MYSQL = """
CREATE TABLE IF NOT EXISTS custom_configs (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    name VARCHAR(255) NOT NULL UNIQUE COMMENT '配置名称（如 email_server）',
    content TEXT NOT NULL COMMENT 'YAML 格式的配置内容',
    description TEXT COMMENT '配置说明',
    created_at VARCHAR(64) NOT NULL COMMENT '创建时间（ISO 8601 UTC）',
    updated_at VARCHAR(64) NOT NULL COMMENT '更新时间（ISO 8601 UTC）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自定义配置表';
"""


class ConfigDB:
    """Store for custom configs."""

    def __init__(self, db: Database):
        self.db = db
        schema = _SCHEMA_MYSQL if self.db.dialect == "mysql" else _SCHEMA_SQLITE
        self.db.executescript(schema)

    def create(self, name: str, content: str, description: str = "") -> dict:
        now = datetime.now(timezone.utc).isoformat()
        config_id = self.db.execute_returning_id(
            """INSERT INTO custom_configs (name, content, description, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (name, content, description, now, now),
        )
        return self.get_by_id(config_id)

    def get_all(self) -> list:
        rows = self.db.fetchall("SELECT * FROM custom_configs ORDER BY created_at DESC")
        return [dict(r) for r in rows]

    def get_by_id(self, config_id: int) -> Optional[dict]:
        row = self.db.fetchone("SELECT * FROM custom_configs WHERE id = ?", (config_id,))
        return dict(row) if row else None

    def get_by_name(self, name: str) -> Optional[dict]:
        row = self.db.fetchone("SELECT * FROM custom_configs WHERE name = ?", (name,))
        return dict(row) if row else None

    def update(self, config_id: int, **kwargs) -> Optional[dict]:
        allowed = {"name", "content", "description"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get_by_id(config_id)
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [config_id]
        self.db.execute(f"UPDATE custom_configs SET {set_clause} WHERE id = ?", tuple(values))
        return self.get_by_id(config_id)

    def delete(self, config_id: int) -> bool:
        self.db.execute("DELETE FROM custom_configs WHERE id = ?", (config_id,))
        return self.get_by_id(config_id) is None
