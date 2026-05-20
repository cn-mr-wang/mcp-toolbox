"""Token management utilities."""

import os
import secrets


def generate_token() -> str:
    """Generate a secure random token (32 hex chars)."""
    return secrets.token_hex(16)


def get_mcp_token(cli_token: str = "") -> str:
    """Get MCP token from environment variable or CLI argument.

    Priority: MCP_TOOLBOX_TOKEN env var > cli_token
    """
    return os.environ.get("MCP_TOOLBOX_TOKEN", "") or cli_token


def filter_tools_by_token(registry_names: list, token_info: dict | None) -> list:
    """Filter tool names based on token permissions.

    Args:
        registry_names: All registered tool names
        token_info: Token dict from store (with allowed_tools field), or None

    Returns:
        List of allowed tool names. Empty list if token is invalid/disabled.
    """
    if token_info is None:
        return []

    if not token_info.get("enabled", False):
        return []

    allowed = token_info.get("allowed_tools")
    if allowed is None:
        # null = all tools allowed
        return list(registry_names)

    # Filter to only tools in the allowed list
    return [name for name in registry_names if name in allowed]
