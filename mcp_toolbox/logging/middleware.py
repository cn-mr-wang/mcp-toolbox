"""Transparent logging middleware for tool executions."""

from mcp_toolbox.core.types import ToolEntry, ToolResult
from mcp_toolbox.executors.base import BaseExecutor
from mcp_toolbox.logging.store import CallLogStore


class LoggingMiddleware:
    """Wraps tool execution with automatic logging.

    This middleware is invisible to tool authors - it records
    every call's input, output, duration, and status to SQLite.
    """

    def __init__(self, store: CallLogStore):
        self.store = store

    def wrap_call(self, entry: ToolEntry, params: dict, executor: BaseExecutor) -> ToolResult:
        """Execute a tool and log the call.

        Args:
            entry: The tool entry from the registry
            params: The input parameters
            executor: The executor to use

        Returns:
            ToolResult from the executor
        """
        result = executor.execute(entry, params)

        self.store.log_call(
            tool_name=entry.name,
            tool_type=entry.tool_type.value,
            input_params=params,
            output=result.output,
            duration_ms=result.duration_ms,
            status="success" if result.success else "error",
            error_message=result.error,
            error_category=result.error_category,
        )

        return result
