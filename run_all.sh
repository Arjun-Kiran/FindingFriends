#!/usr/bin/env bash
#
# Finding Friends — start the game.
#
#   bash run_all.sh              development (default)
#   bash run_all.sh dev
#   bash run_all.sh prod         production: public, one port, built assets
#
# Development runs two servers: vite on :3000 with hot reload, and gunicorn on
# 127.0.0.1:5050. Both are bound to the loopback address and are reachable only
# from this machine.
#
# Production builds the frontend and serves it from gunicorn itself, so the
# page, the REST API and the websocket all share ONE origin on ONE public port.
# That is what lets you hand out a bare address: no port juggling, no CORS
# surface, and a socket that follows whatever address the player typed.
#
# Environment:
#   PORT       production port (default 80)
#   LOG_LEVEL  DEBUG | INFO (default INFO)
set -uo pipefail

if [ -z "${BASH_VERSION:-}" ]; then
    if command -v bash > /dev/null 2>&1; then
        exec bash "$0" "$@"
    fi
    echo "run_all.sh needs bash." >&2
    exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1

MODE="${1:-dev}"
PORT="${PORT:-80}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

case "$MODE" in
    dev|prod) ;;
    -h|--help) sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown mode '$MODE'. Use 'dev' or 'prod'." >&2; exit 2 ;;
esac

# ---------------------------------------------------------------------------
# Development — unchanged behaviour: two servers, loopback only.
# ---------------------------------------------------------------------------
if [ "$MODE" = "dev" ]; then
    echo "Starting Finding Friends (development)..."

    echo "Starting backend..."
    cd backend_code
    bash run_flask_server.sh &
    BACKEND_PID=$!
    cd ..

    # Give the backend a moment to start
    sleep 3

    echo "Starting frontend..."
    cd frontend_code
    bash run_frontend.sh
    FRONTEND_EXIT=$?

    echo "Shutting down backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null

    echo "All services stopped."
    exit $FRONTEND_EXIT
fi

# ---------------------------------------------------------------------------
# Production
# ---------------------------------------------------------------------------
echo "Starting Finding Friends (production) on port $PORT..."

VENV="$ROOT/backend_code/backend_venv"
if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
    echo "No usable virtualenv at backend_code/backend_venv." >&2
    echo "Run 'bash setup.sh' first." >&2
    exit 1
fi

# Ports below 1024 are privileged. Say so now rather than letting gunicorn fail
# with a bind error that does not explain itself.
if [ "$PORT" -lt 1024 ] && [ "$(id -u)" -ne 0 ]; then
    echo "Port $PORT needs root. Either:" >&2
    echo "  sudo -E bash run_all.sh prod          (keeps your environment)" >&2
    echo "  PORT=8080 bash run_all.sh prod        (unprivileged port)" >&2
    exit 1
fi

# --- Build the frontend ----------------------------------------------------
# VITE_SERVER_URL is deliberately EMPTY: that is what tells the client to open
# its socket against the page's own origin. Baked in at build time, so it has
# to be set here and not when the server starts. The build holds no hostname,
# which is why the same one works on an IP, a domain, or localhost.
echo "Building the frontend..."
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
# shellcheck disable=SC1091
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" >/dev/null 2>&1

if ! command -v npm >/dev/null 2>&1; then
    echo "npm is not on PATH. Open a new terminal, or run 'bash setup.sh'." >&2
    exit 1
fi

cd frontend_code || exit 1
if [ -d node_modules ]; then
    npm install --no-fund --no-audit || { echo "npm install failed." >&2; exit 1; }
elif [ -f package-lock.json ]; then
    npm ci --no-fund --no-audit || { echo "npm ci failed." >&2; exit 1; }
else
    npm install --no-fund --no-audit || { echo "npm install failed." >&2; exit 1; }
fi

VITE_SERVER_URL="" npm run build || { echo "Frontend build failed." >&2; exit 1; }
cd "$ROOT" || exit 1
echo "Built frontend_code/dist."

# --- Serve -----------------------------------------------------------------
# Deliberately NOT run_flask_server.sh: that clears the database and runs the
# test suite before serving, which would wipe every game in progress on each
# restart.
#
# --workers must stay 1. broadcast_player_views reads the in-process
# SID_TO_PLAYER dict, so a second worker would silently fail to deliver updates
# to whichever players it did not happen to hold.
cd backend_code || exit 1

ADDRESS="$(hostname -I 2>/dev/null | awk '{print $1}')"
[ -n "$ADDRESS" ] || ADDRESS="<this-host>"
DISPLAY_PORT=""
[ "$PORT" = "80" ] || DISPLAY_PORT=":$PORT"

cat <<BANNER

  Finding Friends is starting on http://${ADDRESS}${DISPLAY_PORT}

  Share that address. One player creates a game and passes the code to the
  rest; five players minimum.

  The page, the API and the websocket are all on this one port, so nothing
  else needs opening. If players outside cannot reach it, check the firewall
  (on a DigitalOcean droplet: 'ufw allow ${PORT}').

  Anyone with the address can join a game. Stop the server with Ctrl+C.

BANNER

exec "$VENV/bin/gunicorn" \
    --worker-class gthread \
    --workers 1 \
    --threads 100 \
    -b "0.0.0.0:$PORT" \
    --access-logfile - \
    Main:app
