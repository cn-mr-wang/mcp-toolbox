"""Java tool executor - runs Java programs via subprocess."""

import json
import os
import subprocess
import time

from mcp_toolbox.core.errors import ErrorCategory, format_error
from mcp_toolbox.core.types import ToolEntry, ToolResult
from mcp_toolbox.executors.base import BaseExecutor
from mcp_toolbox.executors.config_vars import extract_config_vars, resolve_config_vars


def _build_java_args(params: dict, mode: str) -> list[str]:
    """Build Java command-line arguments based on mode.

    Modes:
        json:    ["{'key': 'value', ...}"]  (single JSON string, default)
        args:    ["--key1", "value1", "--key2", "value2"]  (individual flags)
        raw:     ["value1", "value2", ...]  (positional values only, sorted by key)
    """
    if mode == "args":
        args = []
        for key, value in params.items():
            args.append(f"--{key}")
            args.append(str(value))
        return args
    elif mode == "raw":
        return [str(v) for v in params.values()]
    else:  # json (default)
        return [json.dumps(params)]


class JavaExecutor(BaseExecutor):
    """Executes Java tools via subprocess.

    Supports two modes:
    1. JAR mode: java -jar {jar_path} [args]
    2. Source mode: javac + java -cp {classpath} {main_class} [args]

    Args mode (java_args_mode metadata):
        json:  pass params as single JSON string (default)
               java -jar tool.jar '{"name":"alice","age":18}'
        args:  pass as individual --key value flags
               java -jar tool.jar --name alice --age 18
        raw:   pass values as positional args
               java -jar tool.jar alice 18
    """

    def execute(self, entry: ToolEntry, params: dict) -> ToolResult:
        java_home = entry.metadata.get(
            "java_home", os.environ.get("JAVA_HOME", "java")
        )
        # Ensure java binary path
        if java_home == "java" or not java_home.endswith("/java"):
            java_bin = "java"
            javac_bin = "javac"
        else:
            java_bin = os.path.join(java_home, "bin", "java")
            javac_bin = os.path.join(java_home, "bin", "javac")

        args_mode = entry.metadata.get("java_args_mode", "json")
        java_args = _build_java_args(params, args_mode)
        timeout = entry.metadata.get("timeout", 60)

        # Inject config values as Java system properties (-Dconfig.xxx=yyy)
        config_values = extract_config_vars(str(entry.metadata))
        config_props = []
        for key, value in config_values.items():
            prop_name = f"config.{key}".replace(".", "_")
            config_props.extend([f"-D{prop_name}={value}"])

        # Resolve {config:...} in jar_path
        jar_path = entry.metadata.get("jar_path", "")
        jar_path = resolve_config_vars(jar_path) if jar_path else ""

        if jar_path:
            # JAR mode
            cmd = [java_bin] + config_props + ["-jar", jar_path] + java_args
        elif source_path := entry.metadata.get("source_path"):
            # Source compilation mode
            source_path = resolve_config_vars(source_path)
            main_class = entry.metadata.get("main_class", "")
            classpath = entry.metadata.get("classpath", ".")

            # Compile first
            compile_cmd = [javac_bin, "-cp", classpath, source_path]
            try:
                compile_result = subprocess.run(
                    compile_cmd, capture_output=True, text=True, timeout=30
                )
            except subprocess.TimeoutExpired as e:
                msg, category = format_error(e, entry.name)
                return ToolResult(
                    success=False, output=None, error=msg,
                    error_category=category.value, duration_ms=0.0,
                )
            except Exception as e:
                msg, category = format_error(e, entry.name)
                return ToolResult(
                    success=False, output=None, error=msg,
                    error_category=category.value, duration_ms=0.0,
                )

            if compile_result.returncode != 0:
                stderr = compile_result.stderr.strip().split("\n")[0]
                return ToolResult(
                    success=False, output=None,
                    error=f"[execution] Java 编译失败（退出码 {compile_result.returncode}）: {stderr}",
                    error_category=ErrorCategory.EXECUTION.value,
                    duration_ms=0.0,
                )

            cmd = [java_bin] + config_props + ["-cp", classpath, main_class] + java_args
        else:
            return ToolResult(
                success=False, output=None,
                error="[config] 未指定 'jar_path' 或 'source_path'\n建议: 在 @toolbox.tool() 中设置 jar_path 或 source_path 参数",
                error_category=ErrorCategory.CONFIGURATION.value,
                duration_ms=0.0,
            )

        start = time.monotonic()
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            duration = (time.monotonic() - start) * 1000

            if result.returncode != 0:
                stderr = (result.stderr or "").strip().split("\n")[0]
                return ToolResult(
                    success=False, output=result.stdout,
                    error=f"[execution] Java 执行失败（退出码 {result.returncode}）: {stderr}",
                    error_category=ErrorCategory.EXECUTION.value,
                    duration_ms=duration,
                )

            # Try to parse output as JSON
            output = result.stdout.strip()
            try:
                output = json.loads(output)
            except (json.JSONDecodeError, ValueError):
                pass

            return ToolResult(success=True, output=output, duration_ms=duration)
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
