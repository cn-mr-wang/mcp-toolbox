"""Abstract base class for tool executors."""

from abc import ABC, abstractmethod

from mcp_toolbox.core.types import ToolEntry, ToolResult


class BaseExecutor(ABC):
    """Base class for all tool executors."""

    @abstractmethod
    def execute(self, entry: ToolEntry, params: dict) -> ToolResult:
        """Execute a tool with the given parameters.

        Args:
            entry: The tool entry from the registry
            params: The input parameters

        Returns:
            ToolResult with output, error, and duration
        """
