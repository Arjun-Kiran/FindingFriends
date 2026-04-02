#!/bin/bash
echo "Starting Finding Friends..."

# Start backend in the background
echo "Starting backend..."
cd backend_code
bash run_flask_server.sh &
BACKEND_PID=$!
cd ..

# Give the backend a moment to start
sleep 3

# Start frontend in the foreground
echo "Starting frontend..."
cd frontend_code
bash run_frontend.sh
FRONTEND_EXIT=$?

# When frontend exits (Ctrl+C), also kill the backend
echo "Shutting down backend (PID: $BACKEND_PID)..."
kill $BACKEND_PID 2>/dev/null
wait $BACKEND_PID 2>/dev/null

echo "All services stopped."
exit $FRONTEND_EXIT
