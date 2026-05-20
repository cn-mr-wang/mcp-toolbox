"""SQLite schema for call logs."""

CALL_LOGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    tool_type TEXT NOT NULL,
    input_params TEXT NOT NULL,
    output TEXT,
    duration_ms REAL NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    error_category TEXT,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_call_logs_tool_name ON call_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_call_logs_timestamp ON call_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_call_logs_status ON call_logs(status);
"""

# Migration: add error_category column to existing tables
_MIGRATE_ERROR_CATEGORY = """
ALTER TABLE call_logs ADD COLUMN error_category TEXT;
"""

TOKENS_SCHEMA = """
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    allowed_tools TEXT,
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);
"""
