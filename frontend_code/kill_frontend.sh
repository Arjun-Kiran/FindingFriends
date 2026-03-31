#!/bin/bash
echo "Killing frontend processes..."

# Kill react-scripts dev server
pids=$(pgrep -f "react-scripts start")
if [ -n "$pids" ]; then
    echo "Stopping react-scripts (PIDs: $pids)"
    kill $pids 2>/dev/null
else
    echo "No react-scripts processes found."
fi

# Kill any process on port 3000
pids=$(lsof -ti :3000 2>/dev/null)
if [ -n "$pids" ]; then
    echo "Stopping processes on port 3000 (PIDs: $pids)"
    kill $pids 2>/dev/null
else
    echo "No processes on port 3000."
fi

echo "Frontend stopped."
