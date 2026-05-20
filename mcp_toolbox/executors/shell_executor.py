"""Shell tool executor - runs shell commands via subprocess."""

import importlib
import subprocess
import time
from pathlib import Path

from mcp_toolbox.core.errors import ErrorCategory, format_error
from mcp_toolbox.core.types import ToolEntry, ToolResult
from mcp_toolbox.executors.base import BaseExecutor


def _load_file(file_path: str, module_name: str = "") -> str | None:
    """Load file content, resolving path relative to the calling module's directory.

    Used by both ShellExecutor (command_file) and SQLExecutor (query_file).
    """
    path = Path(file_path)

    if path.is_absolute():
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return None

    if module_name:
        try:
            mod = importlib.import_module(module_name)
            mod_file = getattr(mod, "__file__", None)
            if mod_file:
                mod_dir = Path(mod_file).parent
                full_path = mod_dir / path
                if full_path.exists():
                    return full_path.read_text(encoding="utf-8").strip()
        except (ImportError, AttributeError):
            pass

    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path.read_text(encoding="utf-8").strip()

    return None


class ShellExecutor(BaseExecutor):
    """Executes Shell tools using subprocess.run with command templates.

    Command can be specified in two ways:
    1. Inline: command="ls -la {path}"
    2. File:   command_file="scripts/deploy.sh" (relative to the tool module)
    """

    def execute(self, entry: ToolEntry, params: dict) -> ToolResult:
        command_template = entry.metadata.get("command", "")
        command_file = entry.metadata.get("command_file", "")

        # Load command from file if specified
        if command_file and not command_template:
            command_template = _load_file(command_file, entry.module_name)
            if command_template is None:
                return ToolResult(
                    success=False, output=None,
                    error=f"[not_found] 命令文件不存在: {command_file}\n建议: 检查 command_file 路径是否正确",
                    error_category=ErrorCategory.NOT_FOUND.value,
                    duration_ms=0.0,
                )

        if not command_template:
            return ToolResult(
                success=False, output=None,
                error="[config] 未指定 'command' 或 'command_file' 配置\n建议: 在 @toolbox.tool() 中设置 command（内联命令）或 command_file（命令文件路径）",
                error_category=ErrorCategory.CONFIGURATION.value,
                duration_ms=0.0,
            )

        # Interpolate params into command template
        try:
            command = command_template.format(**params)
        except KeyError as e:
            msg, category = format_error(e, entry.name)
            return ToolResult(
                success=False, output=None, error=msg,
                error_category=category.value, duration_ms=0.0,
            )

        timeout = entry.metadata.get("timeout", 30)

        start = time.monotonic()
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = (time.monotonic() - start) * 1000

            if result.returncode != 0:
                return ToolResult(
                    success=False,
                    output=result.stdout,
                    error=f"[execution] 命令执行失败（退出码 {result.returncode}）: {result.stderr.strip().split(chr(10))[0] if result.stderr else '无错误输出'}",
                    error_category=ErrorCategory.EXECUTION.value,
                    duration_ms=duration,
                )

            return ToolResult(
                success=True, output=result.stdout, duration_ms=duration
            )
        except subprocess.TimeoutExpired as e:
            duration = (time.monotonic() - start) * 1000
            msg, category = format_error(e, entry.name)
            return ToolResult(
                success=False, output=None, error=msg,
                error_category=category.value, duration_ms=duration,
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            msg, category = format_error(e, entry.name)
            return ToolResult(
                success=False, output=None, error=msg,
                error_category=category.value, duration_ms=duration,
            )
