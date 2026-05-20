#!/usr/bin/env bash
# Start MCP Toolbox service (macOS / Linux)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$PROJECT_DIR/.mcp_toolbox.pid"
LOG_FILE="$PROJECT_DIR/logs/mcp_toolbox.log"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo -e "${YELLOW}MCP Toolbox is already running (PID: $OLD_PID)${NC}"
        echo "Use scripts/shutdown.sh to stop it first."
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Find Python - prefer venv, fallback to system
PYTHON="$PROJECT_DIR/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON="$(command -v python3 2>/dev/null || command -v python 2>/dev/null)"
fi
if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
    echo -e "${RED}Python not found. Please install Python or create a venv first.${NC}"
    exit 1
fi

echo "Using Python: $PYTHON"

# Start service
echo "Starting MCP Toolbox..."
cd "$PROJECT_DIR"

# Pass through any extra args
# Default: Web UI only (--no-mcp), since MCP stdio mode needs interactive stdin
# Use --no-web for MCP-only mode (must run interactively, not via nohup)
# Use no args for both Web + MCP (must run interactively)
ARGS="${*:---no-mcp}"

PYTHONUNBUFFERED=1 nohup "$PYTHON" -m mcp_toolbox $ARGS > "$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"

# Wait and check if it's still running
sleep 2
if kill -0 "$PID" 2>/dev/null; then
    echo -e "${GREEN}MCP Toolbox started (PID: $PID)${NC}"
    echo "Log: $LOG_FILE"
    # Show admin token if available
    TOKEN_FILE="$PROJECT_DIR/logs/.admin_token"
    if [ -f "$TOKEN_FILE" ]; then
        ADMIN_TOKEN=$(cat "$TOKEN_FILE")
        echo -e "${YELLOW}Admin token: $ADMIN_TOKEN${NC}"
    fi
else
    echo -e "${RED}Failed to start MCP Toolbox. Log output:${NC}"
    echo "---"
    cat "$LOG_FILE" 2>/dev/null || echo "(no log file)"
    echo "---"
    rm -f "$PID_FILE"
    exit 1
fi
