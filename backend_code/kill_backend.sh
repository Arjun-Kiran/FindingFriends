#!/bin/bash
echo "Killing backend processes..."

# Kill gunicorn processes
pids=$(pgrep -f "gunicorn.*Main:app")
if [ -n "$pids" ]; then
    echo "Stopping gunicorn (PIDs: $pids)"
    kill $pids 2>/dev/null
else
    echo "No gunicorn processes found."
fi

# Kill any flask dev server on port 5000
pids=$(lsof -ti :5050 2>/dev/null)
if [ -n "$pids" ]; then
    echo "Stopping processes on port 5050 (PIDs: $pids)"
    kill $pids 2>/dev/null
else
    echo "No processes on port 5050."
fi

echo "Backend stopped."
