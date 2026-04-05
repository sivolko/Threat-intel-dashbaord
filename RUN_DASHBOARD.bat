@echo off
title Threat Intel Dashboard
echo.
echo  =========================================
echo    Threat Intel Dashboard
echo  =========================================
echo.
echo  Starting server on http://localhost:5100
echo  Opening browser...
echo.
echo  Press Ctrl+C to stop the server.
echo.

:: Open browser after a short delay
start "" "http://localhost:5100"

:: Start the Python server
python server.py
if %errorlevel% neq 0 (
    py server.py
)
pause
