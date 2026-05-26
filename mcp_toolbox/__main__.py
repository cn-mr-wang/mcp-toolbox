"""Entry point for `python -m mcp_toolbox`."""

import argparse
import asyncio
import importlib
import importlib.metadata
import importlib.util
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

import uvicorn


def _load_tool_modules(modules: list[str]):
    """Import tool modules to trigger @toolbox.tool() registrations.

    Modules without @toolbox.tool() decorators are loaded but have no effect.
    Import errors are logged as warnings but don't prevent startup.
    """
    for mod_name in modules:
        try:
            importlib.import_module(mod_name)
        except ImportError as e:
            print(f"Warning: Could not import '{mod_name}': {e}")
        except Exception as e:
            print(f"Warning: Error loading '{mod_name}': {e}")


def _install_tool_deps(tools_dir: str) -> None:
    """Auto-install dependencies from tools/requirements.txt if missing.

    Checks each package in requirements.txt against installed packages.
    If any are missing, runs pip install -r to install all.
    """
    tools_path = Path(tools_dir)
    if not tools_path.is_absolute():
        tools_path = Path.cwd() / tools_path

    req_file = tools_path / "requirements.txt"
    if not req_file.exists():
        return

    # Parse package names from requirements.txt (skip comments, blanks, options)
    missing = []
    for line in req_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Extract package name: "pandas>=2.0" -> "pandas", "package[extra]" -> "package"
        match = re.match(r"^([A-Za-z0-9_-]+)", line)
        if not match:
            continue
        pkg_name = match.group(1)
        try:
            importlib.metadata.distribution(pkg_name)
        except importlib.metadata.PackageNotFoundError:
            missing.append(pkg_name)

    if not missing:
        return

    print(f"Installing {len(missing)} missing tool dependencies: {', '.join(missing)}")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Warning: Failed to install some dependencies:\n{result.stderr}")
    else:
        print("Tool dependencies installed successfully.")


def _discover_tool_modules(tools_dir: str = "tools", load_examples: bool = False) -> list[str]:
    """Auto-discover tool modules.

    Args:
        tools_dir: Directory to scan for tool modules (relative to cwd or absolute)
        load_examples: Whether to load example tools from examples/

    Discovery rules:
    1. If load_examples=True, load examples/*_tools.py
    2. Recursively load all *.py files from tools_dir
       - Subdirectories must contain __init__.py to be treated as Python packages
       - __init__.py files are skipped (loaded automatically when the package is imported)
    """
    modules = []

    # Load examples only when explicitly requested
    if load_examples:
        examples_dir = Path(__file__).parent.parent / "examples"
        if examples_dir.exists():
            for f in sorted(examples_dir.glob("*_tools.py")):
                modules.append(f"examples.{f.stem}")

    # Resolve tools_dir: absolute path as-is, relative path based on cwd
    tools_path = Path(tools_dir)
    if not tools_path.is_absolute():
        tools_path = Path.cwd() / tools_path

    if tools_path.exists():
        # The package name is the directory name
        package_name = tools_path.name

        # Detect collision: if a package with the same name is already installed,
        # importing tools as <package_name>.xxx will resolve to the installed
        # package instead of the tools directory. In that case, add the tools
        # directory itself to sys.path so modules are imported without the prefix.
        collision = False
        try:
            spec = importlib.util.find_spec(package_name)
            collision = spec is not None
        except (ModuleNotFoundError, ValueError):
            pass

        if collision:
            # Add tools_path itself to sys.path; subdirs become top-level packages
            if str(tools_path) not in sys.path:
                sys.path.insert(0, str(tools_path))
            for f in sorted(tools_path.rglob("*.py")):
                if f.name == "__init__.py":
                    continue
                rel = f.relative_to(tools_path)
                parts = list(rel.with_suffix("").parts)
                if len(parts) == 1:
                    modules.append(parts[0])
                else:
                    # Nested: check if parent dir is a package (has __init__.py)
                    parent_dir = f.parent
                    if (parent_dir / "__init__.py").exists():
                        modules.append(".".join(parts))
                    else:
                        print(f"Warning: Skipping '{f}': parent '{parent_dir.name}' "
                              f"has no __init__.py")
        else:
            # Normal case: add parent so tools_path.name becomes the package
            parent = tools_path.parent
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))

            for f in sorted(tools_path.rglob("*.py")):
                if f.name == "__init__.py":
                    continue
                # Convert file path to module name
                rel = f.relative_to(tools_path)
                parts = list(rel.with_suffix("").parts)
                module_name = ".".join([package_name] + parts)
                modules.append(module_name)
    else:
        print(f"Warning: Tools directory '{tools_dir}' does not exist")

    return modules


def main():
    parser = argparse.ArgumentParser(description="MCP Toolbox - Generic MCP tool framework")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--modules", nargs="*", help="Tool modules to load (e.g., tools.my_tools)")
    parser.add_argument("--tools-dir", help="Tools directory (default: tools)")
    parser.add_argument("--web-port", type=int, help="Override web UI port")
    parser.add_argument("--web-host", help="Override web UI host")
    parser.add_argument("--db-path", help="Override log database path")
    parser.add_argument("--retention-days", type=int, help="Log retention days (min 1, default 7)")
    parser.add_argument("--no-web", action="store_true", help="Disable web UI")
    parser.add_argument("--no-mcp", action="store_true", help="Disable MCP server (web UI only)")
    parser.add_argument("--transport", choices=["stdio", "http"], help="MCP transport: stdio (default) or http (mount on web server)")
    parser.add_argument("--load-examples", action="store_true", help="Load example tools (for development)")
    parser.add_argument("--admin-token", help="Admin token for Web UI token management")
    parser.add_argument("--token", help="MCP server token (filters available tools by permissions)")
    args = parser.parse_args()

    # Load config
    from mcp_toolbox.config import Config
    config = Config(args.config)

    # Initialize databases
    db_path = args.db_path or config.get("database.log_path")
    retention_days = args.retention_days or config.get("database.retention_days", 7)
    retention_days = max(1, retention_days)

    from mcp_toolbox.core.database import create_database
    from mcp_toolbox.core.log_db import LogDB
    from mcp_toolbox.core.token_db import TokenDB
    from mcp_toolbox.core.config_db import ConfigDB
    from mcp_toolbox.core.config_store import config_store

    db_type = config.get("database.type", "sqlite")
    if db_type == "mysql":
        db = create_database("mysql",
            host=config.get("database.host"),
            port=config.get("database.port", 3306),
            user=config.get("database.user"),
            password=config.get("database.password"),
            database=config.get("database.database"),
        )
    else:
        db = create_database("sqlite", db_path=db_path)

    log_db = LogDB(db=db, retention_days=retention_days)
    token_db = TokenDB(db=db)
    config_db = ConfigDB(db=db)

    # Clean up old logs on startup
    deleted = log_db.cleanup_old_logs()
    if deleted > 0:
        print(f"Cleaned up {deleted} log entries older than {retention_days} days")

    # Load custom configs
    config_store.load(config_db)

    # Determine tools directory
    tools_dir = args.tools_dir or config.get("tools.dir", "tools")

    # Auto-install tool dependencies from tools/requirements.txt
    _install_tool_deps(tools_dir)

    # Determine which tool modules to load
    # Priority: --modules > config > auto-discover
    if args.modules:
        modules = args.modules
    else:
        # Check config for explicit module list
        config_modules = config.get("tools.modules", [])
        if config_modules:
            modules = config_modules
        else:
            # Auto-discover
            load_examples = args.load_examples or config.get("tools.load_examples", False)
            auto_discover = config.get("tools.auto_discover", True)

            modules = []
            if load_examples:
                modules.extend(_discover_tool_modules(tools_dir, load_examples=True))
            if auto_discover:
                modules.extend(_discover_tool_modules(tools_dir, load_examples=False))

    if modules:
        _load_tool_modules(modules)

    from mcp_toolbox.core.registry import registry
    if registry.count() > 0:
        print(f"Loaded {registry.count()} tools: {', '.join(registry.names())}")
    else:
        print(f"No tools loaded. Put tool files in '{tools_dir}/' directory "
              "or use --modules to specify tool modules.")

    # Clean up token permissions: remove tools that no longer exist
    cleaned = token_db.cleanup_tools(registry.names())
    if cleaned > 0:
        print(f"Cleaned up {cleaned} token(s) with non-existent tools")

    # Resolve admin token: CLI > env > config > auto-generate
    admin_token = (
        args.admin_token
        or os.environ.get("MCP_TOOLBOX_ADMIN_TOKEN", "")
        or config.get("admin_token", "")
    )
    if not admin_token and not args.no_web:
        from mcp_toolbox.core.token import generate_token
        admin_token = generate_token()
        print(f"Admin token (auto-generated): {admin_token}")
        print("  Use --admin-token or config.yaml to set a fixed token.")

    # Save admin token to file for easy retrieval (e.g., by start.sh)
    if admin_token and not args.no_web:
        token_file = Path("logs") / ".admin_token"
        token_file.parent.mkdir(exist_ok=True)
        token_file.write_text(admin_token)
        token_file.chmod(0o600)

    # Resolve transport: CLI > config > default
    transport = args.transport or config.get("mcp.transport", "stdio")

    # Prepare MCP server (needed for both stdio and http modes)
    mcp_server = None
    if not args.no_mcp:
        from mcp_toolbox.core.token import get_mcp_token
        from mcp_toolbox.server.mcp_server import create_mcp_server
        mcp_token = get_mcp_token(args.token or "", config.get("mcp.token", ""))
        if transport == "stdio" and mcp_token:
            token_info = token_db.get_by_value(mcp_token)
            if token_info and token_info.get("enabled"):
                print(f"MCP server token: {mcp_token[:8]}... (tools filtered by permissions)")
            else:
                print(f"Warning: MCP token is invalid or disabled")
        elif transport == "stdio" and not mcp_token:
            print("Warning: No token configured. 0 tools will be available.")

        # Build server URL for HTTP auth settings
        server_url = ""
        if transport == "http":
            host = args.web_host or config.get("server.host")
            port = args.web_port or config.get("server.port")
            server_url = f"http://{host}:{port}"

        mcp_server = create_mcp_server(
            log_db, token_db, token=mcp_token, transport=transport, server_url=server_url,
        )

    if transport == "http" and not args.no_mcp:
        # HTTP mode: mount MCP on the web server at /mcp
        if args.no_web:
            print("Error: --transport http requires web server. Remove --no-web.")
            sys.exit(1)

        from mcp_toolbox.web.app import create_app
        web_app = create_app(log_db, token_db, admin_token=admin_token, mcp_server=mcp_server, config_db=config_db)

        print(f"MCP endpoint: {server_url}/mcp")
        print(f"Web UI: {server_url}")
        uvicorn.run(web_app, host=host, port=port, log_level="info")

    else:
        # Stdio mode (default): web UI in background thread, MCP on stdin
        if not args.no_web:
            from mcp_toolbox.web.app import create_app
            web_app = create_app(log_db, token_db, admin_token=admin_token, config_db=config_db)
            host = args.web_host or config.get("server.host")
            port = args.web_port or config.get("server.port")

            web_thread = threading.Thread(
                target=uvicorn.run,
                args=(web_app,),
                kwargs={"host": host, "port": port, "log_level": "info"},
                daemon=True,
            )
            web_thread.start()
            print(f"Web UI: http://{host}:{port}")

        if mcp_server:
            print("MCP server starting on stdio...")
            asyncio.run(mcp_server.run_stdio_async())
        elif not args.no_web:
            print("Running in web-only mode. Use scripts/shutdown.sh to stop, or press Ctrl+C.")
            try:
                while True:
                    threading.Event().wait(1)
            except KeyboardInterrupt:
                print("\nShutting down...")


if __name__ == "__main__":
    main()
