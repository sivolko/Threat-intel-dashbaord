#!/bin/bash
clear
echo ""
echo " ========================================="
echo "   Threat Intel Dashboard"
echo " ========================================="
echo ""
echo " Starting server on http://localhost:5100"
echo " Opening browser..."
echo ""
echo " Press Ctrl+C to stop the server."
echo ""

# Open browser after a short delay
(sleep 2 && xdg-open "http://localhost:5100" 2>/dev/null || open "http://localhost:5100" 2>/dev/null) &

# Start the Python server
if command -v python3 &>/dev/null; then
    python3 server.py
elif command -v python &>/dev/null; then
    python server.py
else
    echo "ERROR: Python not found. Please install Python 3."
    exit 1
fi
