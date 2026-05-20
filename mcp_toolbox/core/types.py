"""Core type definitions for MCP Toolbox."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class ToolType(str, Enum):
    """Supported tool execution types."""
    PYTHON = "python"
    SHELL = "shell"
    JAVA = "java"
    SQL = "sql"


@dataclass
class ToolEntry:
    """A registered tool entry in the registry."""
    name: str
    description: str
    tool_type: ToolType
    handler: Callable
    parameters_schema: dict
    metadata: dict = field(default_factory=dict)
    module_name: str = ""
    is_async: bool = False


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    error_category: Optional[str] = None
    duration_ms: float = 0.0
