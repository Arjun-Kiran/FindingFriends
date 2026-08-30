#!/bin/bash
echo "Killing frontend processes..."

# Kill the vite dev server. Matched via node's argv rather than a bare "vite",
# which would also hit an editor or a shell that happens to have it in the
# command line. The port sweep below is the backstop.
pids=$(pgrep -f "node.*vite")
if [ -n "$pids" ]; then
    echo "Stopping vite (PIDs: $pids)"
    kill $pids 2>/dev/null
else
    echo "No vite processes found."
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
