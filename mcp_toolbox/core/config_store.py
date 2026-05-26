"""Custom config store — module-level singleton for tool access."""

from typing import Any

import yaml


class ConfigStore:
    """In-memory cache of custom configs from the database.

    Provides get() with dotted key path access into YAML content.
    """

    def __init__(self):
        self._configs: dict[str, dict] = {}

    def load(self, config_db) -> None:
        """Load all configs from the database."""
        rows = config_db.get_all()
        self._configs = {}
        for row in rows:
            try:
                parsed = yaml.safe_load(row["content"]) or {}
            except yaml.YAMLError:
                parsed = {}
            self._configs[row["name"]] = parsed

    def reload(self, config_db) -> None:
        """Reload configs from the database (alias for load)."""
        self.load(config_db)

    def get(self, name: str, key_path: str = "", default: Any = None) -> Any:
        """Get a config value.

        Args:
            name: Config name (e.g. "email_server")
            key_path: Dotted path within the config (e.g. "smtp.host").
                      Empty string returns the entire config dict.
            default: Default value if not found.

        Returns:
            The config value, or default if not found.
        """
        config = self._configs.get(name)
        if config is None:
            return default
        if not key_path:
            return config
        keys = key_path.split(".")
        current = config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current


# Module-level singleton
config_store = ConfigStore()


def get_config(name: str, key_path: str = "", default: Any = None) -> Any:
    """Get a custom config value.

    Usage:
        from mcp_toolbox.core.config_store import get_config

        # Get entire config
        cfg = get_config("email_server")

        # Get nested value
        host = get_config("email_server", "smtp.host")

        # With default
        port = get_config("email_server", "smtp.port", default=587)
    """
    return config_store.get(name, key_path, default)
