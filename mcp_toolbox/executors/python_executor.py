"""Python tool executor - calls handler function directly."""

import asyncio
import time

from mcp_toolbox.core.errors import format_error
from mcp_toolbox.core.types import ToolEntry, ToolResult
from mcp_toolbox.executors.base import BaseExecutor


class PythonExecutor(BaseExecutor):
    """Executes Python tools by calling the handler function directly."""

    def execute(self, entry: ToolEntry, params: dict) -> ToolResult:
        start = time.monotonic()
        try:
            if entry.is_async:
                output = asyncio.get_event_loop().run_until_complete(
                    entry.handler(**params)
                )
            else:
                output = entry.handler(**params)
            duration = (time.monotonic() - start) * 1000
            return ToolResult(success=True, output=output, duration_ms=duration)
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            msg, category = format_error(e, entry.name)
            return ToolResult(
                success=False, output=None, error=msg,
                error_category=category.value, duration_ms=duration,
            )
