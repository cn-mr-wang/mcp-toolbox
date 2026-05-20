@echo off
REM Stop MCP Toolbox service (Windows)

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set PID_FILE=%PROJECT_DIR%\.mcp_toolbox.pid

if not exist "%PID_FILE%" (
    echo MCP Toolbox is not running (no PID file found)
    exit /b 0
)

set /p PID=<"%PID_FILE%"

tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul
if !errorlevel! equ 0 (
    echo Stopping MCP Toolbox (PID: %PID%)...
    taskkill /PID %PID% /T >nul 2>&1
    timeout /t 2 /nobreak >nul
    REM Force kill if still running
    tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul
    if !errorlevel! equ 0 (
        echo Force killing...
        taskkill /F /PID %PID% /T >nul 2>&1
    )
    echo MCP Toolbox stopped
) else (
    echo Process %PID% is not running
)

del "%PID_FILE%" 2>nul
