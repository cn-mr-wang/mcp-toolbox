"""User-facing decorator API for defining MCP tools."""

import inspect

from mcp_toolbox.core.registry import registry
from mcp_toolbox.core.schema import generate_schema
from mcp_toolbox.core.types import ToolEntry, ToolType


class Toolbox:
    """The toolbox object users import to define tools.

    Usage:
        from mcp_toolbox.core.decorators import toolbox
        from mcp_toolbox.core.types import ToolType

        @toolbox.tool(
            name="greet",
            type=ToolType.PYTHON,
            description="向某人打招呼",
            param_descriptions={"name": "人名", "greeting": "问候语"},
        )
        def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"
    """

    def tool(
        self,
        name: str = None,
        type: ToolType = ToolType.PYTHON,
        description: str = None,
        param_descriptions: dict = None,
        **kwargs,
    ):
        """Decorator to register a function as an MCP tool.

        Args:
            name: Tool name (defaults to function name)
            type: Execution type - PYTHON, SHELL, JAVA, or SQL
            description: Tool description (defaults to first line of docstring)
            param_descriptions: Dict of {param_name: description} for parameters.
                                Overrides docstring Args if both exist.
            **kwargs: Type-specific metadata (command, jar_path, connection, query, etc.)
        """
        def decorator(func):
            tool_name = name or func.__name__
            tool_desc = description
            if not tool_desc:
                doc = (func.__doc__ or "").strip()
                tool_desc = doc.split("\n")[0] if doc else tool_name

            schema = generate_schema(func, param_descriptions=param_descriptions, **kwargs)

            entry = ToolEntry(
                name=tool_name,
                description=tool_desc,
                tool_type=type,
                handler=func,
                parameters_schema=schema,
                metadata=kwargs,
                module_name=func.__module__,
                is_async=inspect.iscoroutinefunction(func),
            )
            registry.register(entry)
            return func
        return decorator


# Module-level singleton
toolbox = Toolbox()
