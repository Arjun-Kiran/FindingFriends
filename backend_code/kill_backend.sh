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

# Sweep the development port. The pgrep above already covers production
# gunicorn whatever port it bound, so the production port is only swept when
# PORT names it explicitly — blindly sweeping :80 would kill an unrelated web
# server on someone's machine.
for port in 5050 ${PORT:-}; do
    pids=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "Stopping processes on port $port (PIDs: $pids)"
        kill $pids 2>/dev/null
    else
        echo "No processes on port $port."
    fi
done

echo "Backend stopped."
