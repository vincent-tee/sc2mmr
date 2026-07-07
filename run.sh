#!/bin/bash

# SC2MMR Quick Start Script
# This script starts both the backend and frontend services.

# Set absolute base path
BASE_DIR="/home/vtee/projects/sc2mmr"
BACKEND_PORT=8000
FRONTEND_PORT=5175

echo "🚀 Starting SC2MMR - Friend Squad Edition..."

# 1. Start Backend
echo "📡 Starting Backend on port $BACKEND_PORT..."
cd "$BASE_DIR/backend"
# Kill any existing backend process on this port
pkill -f "uvicorn app.main:app"
# Run in background
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT > "$BASE_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

# 2. Wait for Backend
echo "⏳ Waiting for backend to initialize..."
sleep 5
if curl -s "http://localhost:$BACKEND_PORT/health" > /dev/null; then
    echo "✅ Backend is healthy (PID: $BACKEND_PID)"
else
    echo "❌ Backend failed to start. Check backend.log for errors."
    exit 1
fi

# 3. Start Frontend
echo "💻 Starting Frontend on port $FRONTEND_PORT..."
cd "$BASE_DIR/frontend"

# Check if dist exists, if not build it
if [ ! -d "dist" ]; then
    echo "🏗️ First time setup: Building frontend..."
    npm run build
fi

npm run dev -- --port $FRONTEND_PORT &
FRONTEND_PID=$!

echo ""
echo "✨ SC2MMR is now running!"
echo "🔗 Frontend: http://localhost:$FRONTEND_PORT"
echo "🔗 Backend API: http://localhost:$BACKEND_PORT"
echo "📝 Logs: $BASE_DIR/backend.log"
echo ""
echo "To stop everything: pkill -f uvicorn && pkill -f vite"

# Keep script running to monitor or wait
wait
