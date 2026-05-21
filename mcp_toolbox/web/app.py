"""FastAPI application factory for the Web UI dashboard."""

import contextlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from mcp_toolbox.logging.store import CallLogStore


def create_app(log_store: CallLogStore, admin_token: str = "", mcp_server=None) -> FastAPI:
    """Create the FastAPI application.

    Args:
        log_store: Shared call log store instance
        admin_token: Admin token for managing tokens (empty = no auth required)
        mcp_server: Optional FastMCP server instance for HTTP transport

    Returns:
        Configured FastAPI app
    """
    mcp_app = None
    if mcp_server is not None:
        mcp_app = mcp_server.streamable_http_app()

    @contextlib.asynccontextmanager
    async def lifespan(app):
        if mcp_server is not None:
            async with mcp_server.session_manager.run():
                yield
        else:
            yield

    app = FastAPI(title="MCP Toolbox Dashboard", version="0.1.0", lifespan=lifespan)

    templates = Jinja2Templates(
        directory=str(Path(__file__).parent / "templates")
    )

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Store shared state
    app.state.log_store = log_store
    app.state.templates = templates
    app.state.admin_token = admin_token

    # Mount routes
    from mcp_toolbox.web.routes_api import api_router
    from mcp_toolbox.web.routes_pages import page_router

    app.include_router(api_router, prefix="/api")
    app.include_router(page_router)

    # Mount MCP HTTP transport at / (internal route is /mcp)
    if mcp_app:
        app.mount("/", mcp_app)

    return app
