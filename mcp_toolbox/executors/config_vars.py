"""Config variable substitution for tool templates.

Supports {config:name.key} syntax to inject custom config values
into Shell commands, SQL queries/connections, and Java args.
"""

import re

from mcp_toolbox.core.config_store import get_config

# Pattern: {config:name.key.path} or {config:name}
_CONFIG_VAR_PATTERN = re.compile(r"\{config:([^}]+)\}")


def resolve_config_vars(template: str) -> str:
    """Replace {config:name.key} patterns with config values.

    Args:
        template: String containing {config:...} placeholders

    Returns:
        String with config variables replaced by their values.
        Missing configs are replaced with empty string.
    """
    def _replace(match):
        expr = match.group(1).strip()
        # Split on first dot: "email_server.smtp.host" -> ("email_server", "smtp.host")
        if "." in expr:
            name, key_path = expr.split(".", 1)
        else:
            name, key_path = expr, ""

        value = get_config(name, key_path, default="")
        return str(value) if value is not None else ""

    return _CONFIG_VAR_PATTERN.sub(_replace, template)


def extract_config_vars(template: str) -> dict:
    """Extract all {config:...} variables and their resolved values.

    Args:
        template: String containing {config:...} placeholders

    Returns:
        Dict of {placeholder_expr: resolved_value}
    """
    result = {}
    for match in _CONFIG_VAR_PATTERN.finditer(template):
        expr = match.group(1).strip()
        if "." in expr:
            name, key_path = expr.split(".", 1)
        else:
            name, key_path = expr, ""

        value = get_config(name, key_path, default="")
        result[expr] = str(value) if value is not None else ""
    return result
