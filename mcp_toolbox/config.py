"""Configuration loader with defaults."""

import copy
from pathlib import Path
from typing import Any

import yaml

DEFAULTS = {
    "server": {"host": "127.0.0.1", "port": 8080},
    "mcp": {"transport": "stdio"},
    "database": {"type": "sqlite", "log_path": "mcp_toolbox.db", "retention_days": 7,
                 "host": "localhost", "port": 3306, "user": "root", "password": "", "database": "mcp_toolbox"},
    "java": {"java_home": None},
    "tools": {
        "dir": "tools",         # 工具目录（相对路径或绝对路径）
        "modules": [],          # 显式指定工具模块列表（优先级最高）
        "auto_discover": True,  # 自动发现工具目录下的 .py 文件
        "load_examples": False, # 是否加载示例工具（生产环境应关闭）
    },
}


class Config:
    """YAML-based configuration with sensible defaults."""

    def __init__(self, config_path: str = None):
        self._data = copy.deepcopy(DEFAULTS)
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                user_cfg = yaml.safe_load(f) or {}
            self._deep_merge(self._data, user_cfg)

    def get(self, dotted_key: str, default=None) -> Any:
        """Get config value by dotted key: 'server.port' -> 8080."""
        keys = dotted_key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        return val if val is not None else default

    def _deep_merge(self, base: dict, override: dict):
        """Deep merge override into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
