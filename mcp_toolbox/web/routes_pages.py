"""HTML page routes for the MCP Toolbox dashboard."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from mcp_toolbox.core.registry import registry

page_router = APIRouter()


def _tool_to_dict(entry) -> dict:
    """Convert ToolEntry to a plain dict for templates."""
    return {
        "name": entry.name,
        "description": entry.description,
        "tool_type": entry.tool_type,
        "parameters_schema": entry.parameters_schema,
        "metadata": entry.metadata,
        "module_name": entry.module_name,
        "is_async": entry.is_async,
    }


@page_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard home page with summary stats."""
    store = request.app.state.log_store
    stats = store.get_stats()
    tools = [_tool_to_dict(t) for t in registry.get_all()]
    return request.app.state.templates.TemplateResponse(
        request,
        "dashboard.html",
        {"stats": stats, "tools": tools},
    )


@page_router.get("/tools", response_class=HTMLResponse)
async def tools_list(request: Request):
    """Tools list page."""
    tools = [_tool_to_dict(t) for t in registry.get_all()]
    return request.app.state.templates.TemplateResponse(
        request,
        "tools.html",
        {"tools": tools},
    )


@page_router.get("/tools/{name}", response_class=HTMLResponse)
async def tool_detail(request: Request, name: str):
    """Single tool detail page."""
    entry = registry.get(name)
    if not entry:
        return HTMLResponse(content=f"<h1>Tool '{name}' not found</h1>", status_code=404)

    store = request.app.state.log_store
    recent_logs = store.get_logs(tool_name=name, limit=20)
    tool_stats = store.get_tool_stats(name)

    # Get source code for Python tools
    source = None
    if entry.tool_type.value == "python":
        import inspect
        try:
            source = inspect.getsource(entry.handler)
        except (OSError, TypeError):
            source = "# Source not available"

    tool = _tool_to_dict(entry)

    return request.app.state.templates.TemplateResponse(
        request,
        "tool_detail.html",
        {
            "tool": tool,
            "source": source,
            "logs": recent_logs,
            "stats": tool_stats,
        },
    )


@page_router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Call logs page with filters."""
    store = request.app.state.log_store
    logs = store.get_logs(limit=200)
    tools = [_tool_to_dict(t) for t in registry.get_all()]
    return request.app.state.templates.TemplateResponse(
        request,
        "logs.html",
        {"logs": logs, "tools": tools},
    )


@page_router.get("/access", response_class=HTMLResponse)
async def tokens_page(request: Request):
    """Token management page."""
    store = request.app.state.log_store
    admin_token = request.app.state.admin_token
    admin_required = bool(admin_token)

    # Check if already authenticated via cookie
    authenticated = False
    if admin_required:
        cookie_token = request.cookies.get("admin_token", "")
        authenticated = cookie_token == admin_token

    tokens = store.get_tokens() if (not admin_required or authenticated) else []
    tools = registry.get_all()
    tool_info = {t.name: t.description for t in tools}
    tool_names = registry.names()
    return request.app.state.templates.TemplateResponse(
        request,
        "tokens.html",
        {
            "tokens": tokens,
            "tool_names": tool_names,
            "tool_info": tool_info,
            "admin_required": admin_required,
            "authenticated": authenticated,
        },
    )
