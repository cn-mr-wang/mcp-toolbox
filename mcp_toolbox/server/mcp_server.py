"""FastMCP server integration - bridges registry to MCP protocol."""

import asyncio
import inspect
import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_toolbox.core.registry import registry
from mcp_toolbox.core.token import filter_tools_by_token
from mcp_toolbox.core.types import ToolEntry, ToolResult
from mcp_toolbox.executors import executor_registry
from mcp_toolbox.logging.middleware import LoggingMiddleware


# Map JSON Schema types to Python types for annotations
_SCHEMA_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _build_annotations(schema: dict) -> dict:
    """Convert JSON Schema properties to Python type annotations."""
    annotations = {}
    properties = schema.get("properties", {})
    for name, prop in properties.items():
        schema_type = prop.get("type", "string")
        annotations[name] = _SCHEMA_TYPE_MAP.get(schema_type, str)
    return annotations


def _create_dynamic_tool_func(entry: ToolEntry, middleware: LoggingMiddleware):
    """Create a wrapper function that FastMCP can introspect.

    The wrapper has proper __name__, __doc__, and __annotations__
    so FastMCP generates correct tool schemas.
    """
    tool_entry = entry
    tool_middleware = middleware
    tool_executor = executor_registry.get(entry.tool_type)

    # Build the actual handler
    async def _async_handler(**kwargs):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: tool_middleware.wrap_call(tool_entry, kwargs, tool_executor)
        )
        if not result.success:
            return result.error  # Already formatted by executor
        if isinstance(result.output, str):
            return result.output
        return json.dumps(result.output, ensure_ascii=False, default=str)

    def _sync_handler(**kwargs):
        result = tool_middleware.wrap_call(tool_entry, kwargs, tool_executor)
        if not result.success:
            return result.error  # Already formatted by executor
        if isinstance(result.output, str):
            return result.output
        return json.dumps(result.output, ensure_ascii=False, default=str)

    # Choose async or sync based on handler
    if entry.is_async:
        handler = _async_handler
    else:
        handler = _sync_handler

    # Set metadata for FastMCP introspection
    handler.__name__ = entry.name
    handler.__doc__ = entry.description
    handler.__annotations__ = _build_annotations(entry.parameters_schema)

    # Build a proper signature from the schema
    params = []
    properties = entry.parameters_schema.get("properties", {})
    required_fields = set(entry.parameters_schema.get("required", []))

    for name, prop in properties.items():
        tp = _SCHEMA_TYPE_MAP.get(prop.get("type", "string"), str)
        if name in required_fields:
            param = inspect.Parameter(
                name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=tp
            )
        else:
            default = prop.get("default")
            param = inspect.Parameter(
                name, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default, annotation=tp,
            )
        params.append(param)

    handler.__signature__ = inspect.Signature(params)

    return handler


def create_mcp_server(log_store, token: str = "") -> FastMCP:
    """Create and configure the FastMCP server.

    Reads registered tools from the registry, filters by token permissions,
    and creates corresponding MCP tool functions with logging middleware.

    Args:
        log_store: Call log store instance
        token: If set, only tools allowed by this token are registered
    """
    mcp = FastMCP(
        "mcp-toolbox",
        instructions="Generic MCP toolbox with Python, Shell, Java, and SQL tools.",
    )
    middleware = LoggingMiddleware(log_store)

    # Get all registered entries
    entries = registry.get_all()

    # Filter by token if provided
    if token:
        token_info = log_store.get_token_by_value(token)
        allowed = filter_tools_by_token(registry.names(), token_info)
        if not allowed:
            print(f"Warning: Token is invalid, disabled, or has no allowed tools. "
                  f"0 tools will be available.")
        entries = [e for e in entries if e.name in allowed]

    for entry in entries:
        handler = _create_dynamic_tool_func(entry, middleware)
        mcp.tool(
            name=entry.name,
            description=entry.description,
        )(handler)

    return mcp
