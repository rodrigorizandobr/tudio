#!/bin/bash
PID_FILE="tudio_pid.txt"

echo "============================================"
echo "   Tudio V2 - Shutdown Script"
echo "============================================"

# Stop Backend (Uvicorn) on port 8000
echo "Checking for Backend processes on port 8000..."
# Kill ALL uvicorn workers first (avoids stale in-memory code between restarts)
pkill -9 -f "uvicorn" 2>/dev/null
sleep 1
BACKEND_PID=$(lsof -ti:8000 2>/dev/null)
if [ -n "$BACKEND_PID" ]; then
    echo "Stopping Backend (PID: $BACKEND_PID)..."
    kill -9 $BACKEND_PID 2>/dev/null
    echo "Backend stopped."
else
    echo "No Backend process found on port 8000."
fi

# Stop Frontend (Vite) on port 5173
echo "Checking for Frontend processes on port 5173..."
FRONTEND_PID=$(lsof -ti:5173)
if [ -n "$FRONTEND_PID" ]; then
    echo "Stopping Frontend (PID: $FRONTEND_PID)..."
    kill -9 $FRONTEND_PID
    echo "Frontend stopped."
else
    echo "No Frontend process found on port 5173."
fi

# Cleanup PID file just in case
if [ -f "$PID_FILE" ]; then
    rm "$PID_FILE"
fi

echo "Shutdown sequence complete."
echo "============================================"

