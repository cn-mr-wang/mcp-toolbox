"""REST API endpoints for the MCP Toolbox dashboard."""

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import JSONResponse

from mcp_toolbox.core.registry import registry
from mcp_toolbox.core.token import generate_token
from mcp_toolbox.executors import executor_registry

api_router = APIRouter()


def _check_admin(request: Request, x_admin_token: str = Header(default="")) -> bool:
    """Check if the request has valid admin token."""
    admin_token = request.app.state.admin_token
    if not admin_token:
        return True  # No admin token configured = open access
    # Check header or cookie
    if x_admin_token == admin_token:
        return True
    cookie_token = request.cookies.get("admin_token", "")
    return cookie_token == admin_token


@api_router.get("/tools")
def list_tools():
    """List all registered tools."""
    tools = registry.get_all()
    return [
        {
            "name": t.name,
            "type": t.tool_type.value,
            "description": t.description,
            "parameters": t.parameters_schema,
            "module": t.module_name,
            "is_async": t.is_async,
        }
        for t in tools
    ]


@api_router.get("/tools/{name}")
def get_tool(name: str):
    """Get a single tool's details."""
    entry = registry.get(name)
    if not entry:
        return {"error": f"Tool '{name}' not found"}

    tool_info = {
        "name": entry.name,
        "type": entry.tool_type.value,
        "description": entry.description,
        "parameters": entry.parameters_schema,
        "metadata": entry.metadata,
        "module": entry.module_name,
        "is_async": entry.is_async,
    }

    # Add source code for Python tools
    if entry.tool_type.value == "python":
        import inspect
        try:
            tool_info["source"] = inspect.getsource(entry.handler)
        except (OSError, TypeError):
            tool_info["source"] = "# Source not available"

    return tool_info


@api_router.post("/tools/{name}/test")
async def test_tool(name: str, request: Request):
    """Test a tool without logging the call."""
    import time

    entry = registry.get(name)
    if not entry:
        return JSONResponse({"error": f"Tool '{name}' not found"}, status_code=404)

    body = await request.json()
    params = body.get("params", {})

    # Type coercion based on schema
    properties = entry.parameters_schema.get("properties", {})
    for key, prop in properties.items():
        if key in params:
            val = params[key]
            ptype = prop.get("type", "string")
            try:
                if ptype == "integer":
                    params[key] = int(val) if val != "" else prop.get("default")
                elif ptype == "number":
                    params[key] = float(val) if val != "" else prop.get("default")
                elif ptype == "boolean":
                    params[key] = val in (True, "true", "True", "1", "on")
                elif ptype in ("array", "object") and isinstance(val, str):
                    params[key] = __import__("json").loads(val)
            except (ValueError, TypeError):
                pass

    # Remove empty string params that have defaults
    for key, prop in properties.items():
        if key in params and params[key] == "" and "default" in prop:
            params[key] = prop["default"]
        elif key in params and params[key] == "" and key not in entry.parameters_schema.get("required", []):
            del params[key]

    executor = executor_registry.get(entry.tool_type)
    result = executor.execute(entry, params)

    output = result.output
    if not isinstance(output, str):
        try:
            output = __import__("json").dumps(output, ensure_ascii=False, indent=2, default=str)
        except Exception:
            output = str(output)

    return {
        "success": result.success,
        "output": output,
        "error": result.error,
        "error_category": result.error_category,
        "duration_ms": round(result.duration_ms, 1),
    }


@api_router.get("/logs")
def list_logs(
    request: Request,
    tool_name: str = Query(None),
    status: str = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
):
    """Get call logs with optional filters."""
    store = request.app.state.log_store
    logs = store.get_logs(
        tool_name=tool_name, status=status, limit=limit, offset=offset
    )
    return {
        "logs": logs,
        "limit": limit,
        "offset": offset,
        "filters": {"tool_name": tool_name, "status": status},
    }


@api_router.get("/logs/{log_id}")
def get_log(log_id: int, request: Request):
    """Get a single log entry by ID."""
    store = request.app.state.log_store
    log = store.get_log_by_id(log_id)
    if not log:
        return {"error": f"Log entry {log_id} not found"}
    return log


@api_router.get("/stats")
def get_stats(request: Request):
    """Get summary statistics."""
    store = request.app.state.log_store
    return store.get_stats()


@api_router.get("/stats/{tool_name}")
def get_tool_stats(tool_name: str, request: Request):
    """Get stats for a specific tool."""
    store = request.app.state.log_store
    return store.get_tool_stats(tool_name)


# ── Token Management API ───────────────────────────────────────────


@api_router.post("/tokens/auth")
async def token_auth(request: Request):
    """Verify admin token and set cookie."""
    body = await request.json()
    token = body.get("token", "")
    admin_token = request.app.state.admin_token
    if not admin_token:
        return JSONResponse({"ok": True, "message": "Admin token not configured, open access"})
    if token != admin_token:
        return JSONResponse({"ok": False, "message": "Invalid token"}, status_code=401)
    resp = JSONResponse({"ok": True})
    resp.set_cookie("admin_token", token, httponly=True, samesite="lax")
    return resp


@api_router.get("/tokens")
def list_tokens(request: Request, x_admin_token: str = Header(default="")):
    """List all tokens. Requires admin."""
    if not _check_admin(request, x_admin_token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    store = request.app.state.log_store
    return store.get_tokens()


@api_router.post("/tokens")
async def create_token(request: Request, x_admin_token: str = Header(default="")):
    """Create a new token. Requires admin."""
    if not _check_admin(request, x_admin_token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    body = await request.json()
    name = body.get("name", "")
    allowed_tools = body.get("allowed_tools")  # None = all tools
    if not name:
        return JSONResponse({"error": "Name is required"}, status_code=400)

    token_str = generate_token()
    store = request.app.state.log_store
    token = store.create_token(name=name, token=token_str, allowed_tools=allowed_tools)
    return token


@api_router.put("/tokens/{token_id}")
async def update_token(token_id: int, request: Request, x_admin_token: str = Header(default="")):
    """Update a token. Requires admin."""
    if not _check_admin(request, x_admin_token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    body = await request.json()
    store = request.app.state.log_store
    token = store.update_token(token_id, **body)
    if not token:
        return JSONResponse({"error": "Token not found"}, status_code=404)
    return token


@api_router.delete("/tokens/{token_id}")
def delete_token(token_id: int, request: Request, x_admin_token: str = Header(default="")):
    """Delete a token. Requires admin."""
    if not _check_admin(request, x_admin_token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    store = request.app.state.log_store
    if store.delete_token(token_id):
        return {"ok": True}
    return JSONResponse({"error": "Token not found"}, status_code=404)
