"""Unified error handling for MCP Toolbox.

Provides error classification and friendly message formatting
so that MCP agents can understand what went wrong and how to fix it.
"""

import asyncio
import subprocess
from enum import Enum


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    PERMISSION = "permission"
    NOT_FOUND = "not_found"
    PARAMETER = "parameter"
    EXECUTION = "execution"
    CONFIGURATION = "config"
    UNKNOWN = "unknown"


_SUGGESTIONS = {
    ErrorCategory.TIMEOUT: "增加 timeout 配置或优化查询/命令",
    ErrorCategory.CONNECTION: "检查数据库连接配置和网络连通性",
    ErrorCategory.PERMISSION: "检查文件或数据库的读写权限",
    ErrorCategory.NOT_FOUND: "检查文件路径、依赖或资源是否存在",
    ErrorCategory.PARAMETER: "检查传入参数的类型和值是否正确",
    ErrorCategory.EXECUTION: "查看错误详情，检查程序逻辑",
    ErrorCategory.CONFIGURATION: "安装缺失的依赖包或检查配置",
    ErrorCategory.UNKNOWN: "查看详细错误信息，联系工具作者",
}

# Exception type -> category mapping (order matters, first match wins)
_ERROR_RULES: list[tuple[type, ErrorCategory]] = [
    # Timeout
    (subprocess.TimeoutExpired, ErrorCategory.TIMEOUT),
    (TimeoutError, ErrorCategory.TIMEOUT),
    (asyncio.TimeoutError, ErrorCategory.TIMEOUT),
    # Permission
    (PermissionError, ErrorCategory.PERMISSION),
    # Not found
    (FileNotFoundError, ErrorCategory.NOT_FOUND),
    (ModuleNotFoundError, ErrorCategory.NOT_FOUND),
    # Connection (check by exception type + message patterns)
    (ConnectionRefusedError, ErrorCategory.CONNECTION),
    (ConnectionResetError, ErrorCategory.CONNECTION),
    (BrokenPipeError, ErrorCategory.CONNECTION),
    (OSError, ErrorCategory.CONNECTION),  # broad, but covers network errors
    # Parameter
    (KeyError, ErrorCategory.PARAMETER),
    (TypeError, ErrorCategory.PARAMETER),
    (ValueError, ErrorCategory.PARAMETER),
    # Configuration
    (ImportError, ErrorCategory.CONFIGURATION),
    # Execution
    (subprocess.CalledProcessError, ErrorCategory.EXECUTION),
    (RuntimeError, ErrorCategory.EXECUTION),
]

# Message patterns for finer classification when exception type is too broad
_CONNECTION_PATTERNS = [
    "connection refused", "could not connect", "no route to host",
    "network unreachable", "connection timed out", "connection reset",
    "name or service not known", "nodename nor servname provided",
    "authentication failed", "password authentication",
    "database is locked", "too many connections",
]

_PERMISSION_PATTERNS = [
    "permission denied", "readonly", "read-only", "access denied",
    "not allowed", "forbidden",
]

_NOT_FOUND_PATTERNS = [
    "no such file", "not found", "does not exist", "no such directory",
    "no such table", "no such column", "no such index",
]

_EXECUTION_PATTERNS = [
    "syntax error", "near \"", "ambiguous column",
]


def _match_message_patterns(message: str, patterns: list[str]) -> bool:
    """Check if error message matches any of the patterns."""
    lower = message.lower()
    return any(p in lower for p in patterns)


def classify_error(exc: Exception) -> ErrorCategory:
    """Classify an exception into an error category.

    Uses exception type first, then falls back to message pattern matching
    for more specific classification.
    """
    message = str(exc)

    # First pass: match by exception type
    for exc_type, category in _ERROR_RULES:
        if isinstance(exc, exc_type):
            # For broad types like OSError, refine by message
            if exc_type is OSError:
                if _match_message_patterns(message, _PERMISSION_PATTERNS):
                    return ErrorCategory.PERMISSION
                if _match_message_patterns(message, _NOT_FOUND_PATTERNS):
                    return ErrorCategory.NOT_FOUND
                return ErrorCategory.CONNECTION
            return category

    # Second pass: message pattern matching for unknown exceptions
    if _match_message_patterns(message, _CONNECTION_PATTERNS):
        return ErrorCategory.CONNECTION
    if _match_message_patterns(message, _PERMISSION_PATTERNS):
        return ErrorCategory.PERMISSION
    if _match_message_patterns(message, _NOT_FOUND_PATTERNS):
        return ErrorCategory.NOT_FOUND
    if _match_message_patterns(message, _EXECUTION_PATTERNS):
        return ErrorCategory.EXECUTION

    return ErrorCategory.UNKNOWN


def format_error(exc: Exception, tool_name: str = "", category: ErrorCategory = None) -> tuple[str, str]:
    """Format an exception into a friendly error message.

    Returns:
        (formatted_message, category) - the formatted message and the error category
    """
    if category is None:
        category = classify_error(exc)

    suggestion = _SUGGESTIONS.get(category, _SUGGESTIONS[ErrorCategory.UNKNOWN])
    raw = str(exc).split("\n")[0]  # first line only

    # Special formatting for known exceptions
    if isinstance(exc, subprocess.TimeoutExpired):
        cmd = exc.cmd if isinstance(exc.cmd, str) else " ".join(exc.cmd) if exc.cmd else ""
        msg = f"[{category.value}] 命令执行超时（{exc.timeout}s）: {cmd}"
    elif isinstance(exc, subprocess.CalledProcessError):
        stderr = (exc.stderr or "").strip().split("\n")[0]
        msg = f"[{category.value}] 命令执行失败（退出码 {exc.returncode}）: {stderr or raw}"
    elif isinstance(exc, KeyError):
        msg = f"[{category.value}] 缺少必要参数: {exc}"
    elif isinstance(exc, (FileNotFoundError,)):
        msg = f"[{category.value}] 文件或路径不存在: {exc.filename or raw}"
    elif isinstance(exc, (ConnectionRefusedError, ConnectionResetError, BrokenPipeError)):
        msg = f"[{category.value}] 数据库连接失败: {raw}"
    elif isinstance(exc, ImportError) or isinstance(exc, ModuleNotFoundError):
        msg = f"[{category.value}] 缺少依赖: {raw}"
    else:
        msg = f"[{category.value}] {raw}"

    if tool_name:
        msg = f"工具 '{tool_name}' 执行失败: {msg}"

    return f"{msg}\n建议: {suggestion}", category
