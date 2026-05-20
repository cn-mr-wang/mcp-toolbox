"""Tool registry - singleton store for registered tools."""

from typing import Dict, List, Optional

from mcp_toolbox.core.types import ToolEntry, ToolType


class ToolRegistry:
    """Central registry for all MCP tools."""

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}

    def register(self, entry: ToolEntry) -> None:
        """Register a tool. Raises ValueError on duplicate name."""
        if entry.name in self._tools:
            raise ValueError(f"Tool '{entry.name}' already registered")
        self._tools[entry.name] = entry

    def get(self, name: str) -> Optional[ToolEntry]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_all(self) -> List[ToolEntry]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_by_type(self, tool_type: ToolType) -> List[ToolEntry]:
        """Get tools filtered by type."""
        return [e for e in self._tools.values() if e.tool_type == tool_type]

    def names(self) -> List[str]:
        """Get sorted list of all tool names."""
        return sorted(self._tools.keys())

    def count(self) -> int:
        """Get total number of registered tools."""
        return len(self._tools)

    def clear(self) -> None:
        """Remove all registered tools."""
        self._tools.clear()


# Module-level singleton
registry = ToolRegistry()
