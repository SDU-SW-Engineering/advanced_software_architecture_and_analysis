#!/bin/bash
echo "🍝 Starting Pasta Production Dashboard..."
echo ""

# Start backend server in background
echo "Starting backend server..."
cd "$(dirname "$0")"
node server/server.js &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start React client
echo "Starting React dashboard..."
cd client
npm start &
FRONTEND_PID=$!

echo ""
echo "Dashboard starting!"
echo "Backend server PID: $BACKEND_PID"
echo "Frontend server PID: $FRONTEND_PID"
echo ""
echo "Dashboard will be available at: http://localhost:3000"
echo "Backend API available at: http://localhost:3001"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for interrupt
trap 'echo "Stopping servers..."; kill $BACKEND_PID $FRONTEND_PID; exit' INT
wait