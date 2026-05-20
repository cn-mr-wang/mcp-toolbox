@echo off
REM Start MCP Toolbox service (Windows)

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set PID_FILE=%PROJECT_DIR%\.mcp_toolbox.pid
set LOG_FILE=%PROJECT_DIR%\logs\mcp_toolbox.log

REM Check if already running
if exist "%PID_FILE%" (
    set /p OLD_PID=<"%PID_FILE%"
    tasklist /FI "PID eq !OLD_PID!" 2>nul | find "!OLD_PID!" >nul
    if !errorlevel! equ 0 (
        echo MCP Toolbox is already running (PID: !OLD_PID!)
        echo Use scripts\shutdown.bat to stop it first.
        exit /b 1
    ) else (
        del "%PID_FILE%"
    )
)

REM Create logs directory
if not exist "%PROJECT_DIR%\logs" mkdir "%PROJECT_DIR%\logs"

REM Find Python - prefer venv, fallback to system
set PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe
if not exist "!PYTHON!" (
    set PYTHON=python
)

echo Using Python: !PYTHON!

REM Start service
echo Starting MCP Toolbox...
cd /d "%PROJECT_DIR%"

REM Default: Web UI only (--no-mcp)
REM Pass custom args via: start.bat --no-web
set ARGS=%*
if "!ARGS!"=="" set ARGS=--no-mcp

start /b !PYTHON! -m mcp_toolbox !ARGS! > "%LOG_FILE%" 2>&1

timeout /t 2 /nobreak >nul

REM Check if log has content (process may have failed)
for %%A in ("%LOG_FILE%") do if %%~zA==0 (
    echo MCP Toolbox may have failed. Check log: %LOG_FILE%
) else (
    echo MCP Toolbox started. Log: %LOG_FILE%
)
