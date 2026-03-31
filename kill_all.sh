#!/bin/bash
echo "Stopping all Finding Friends processes..."

bash backend_code/kill_backend.sh
bash frontend_code/kill_frontend.sh

echo "All services stopped."
