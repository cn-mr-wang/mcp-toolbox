from mcp_toolbox.executors.base import BaseExecutor
from mcp_toolbox.executors.python_executor import PythonExecutor
from mcp_toolbox.executors.shell_executor import ShellExecutor
from mcp_toolbox.executors.java_executor import JavaExecutor
from mcp_toolbox.executors.sql_executor import SQLExecutor
from mcp_toolbox.core.types import ToolType


class ExecutorRegistry:
    """Maps ToolType to executor instance."""

    def __init__(self):
        self._executors = {
            ToolType.PYTHON: PythonExecutor(),
            ToolType.SHELL: ShellExecutor(),
            ToolType.JAVA: JavaExecutor(),
            ToolType.SQL: SQLExecutor(),
        }

    def get(self, tool_type: ToolType) -> BaseExecutor:
        return self._executors[tool_type]


executor_registry = ExecutorRegistry()
