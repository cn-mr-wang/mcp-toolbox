#!/usr/bin/env bash
# Stop MCP Toolbox service (macOS / Linux)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$PROJECT_DIR/.mcp_toolbox.pid"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

if [ ! -f "$PID_FILE" ]; then
    echo -e "${RED}MCP Toolbox is not running (no PID file found)${NC}"
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping MCP Toolbox (PID: $PID)..."
    kill "$PID"

    # Wait for process to exit
    for i in $(seq 1 10); do
        if ! kill -0 "$PID" 2>/dev/null; then
            break
        fi
        sleep 0.5
    done

    # Force kill if still running
    if kill -0 "$PID" 2>/dev/null; then
        echo "Force killing..."
        kill -9 "$PID" 2>/dev/null || true
    fi

    echo -e "${GREEN}MCP Toolbox stopped${NC}"
else
    echo -e "${RED}Process $PID is not running${NC}"
fi

rm -f "$PID_FILE"
