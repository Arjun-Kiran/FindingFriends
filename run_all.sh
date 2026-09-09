#!/usr/bin/env bash
#
# Finding Friends — start the game.
#
#   bash run_all.sh              development (default)
#   bash run_all.sh dev
#   bash run_all.sh prod         production: public, one port, built assets
#   bash run_all.sh logs         the last production log
#   bash run_all.sh logs -f      follow it live
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
# Production keeps a log of every run under ./logs, so there is something to
# read after the fact. Nothing to switch on.
#
# Environment:
#   PORT       production port (default 80)
#   LOG_LEVEL  DEBUG | INFO (default INFO)
#   LOG_DIR    where production logs are written (default ./logs)
#   LOG_KEEP   how many past runs to keep (default 10)
set -uo pipefail

# Re-exec under bash if started some other way. `sh run_all.sh` is the case
# worth naming: on macOS /bin/sh IS bash, so BASH_VERSION is set and the old
# check passed, but it runs in POSIX mode where a few bash constructs are a
# syntax error rather than a missing feature. POSIXLY_CORRECT is exported in
# that mode, so it has to go or the new shell lands straight back in it.
if [ -z "${BASH_VERSION:-}" ] || (shopt -qo posix) 2>/dev/null; then
    if command -v bash > /dev/null 2>&1; then
        unset POSIXLY_CORRECT
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
LOG_DIR="${LOG_DIR:-$ROOT/logs}"
LOG_KEEP="${LOG_KEEP:-10}"

case "$MODE" in
    dev|prod|logs) ;;
    # Print the comment block at the top of this file, however long it grows.
    -h|--help) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    *) echo "Unknown mode '$MODE'. Use 'dev', 'prod' or 'logs'." >&2; exit 2 ;;
esac

# ---------------------------------------------------------------------------
# Logs — read back what a production run recorded.
# ---------------------------------------------------------------------------
if [ "$MODE" = "logs" ]; then
    LATEST="$LOG_DIR/latest.log"
    # The symlink is the normal route; fall back to the newest file in case it
    # was removed, or the logs were copied off another machine without it.
    if [ ! -e "$LATEST" ]; then
        LATEST="$(ls -1t "$LOG_DIR"/prod-*.log 2>/dev/null | head -n 1)"
    fi
    if [ -z "$LATEST" ] || [ ! -e "$LATEST" ]; then
        echo "No production logs in $LOG_DIR yet." >&2
        echo "One is written the next time you run 'bash run_all.sh prod'." >&2
        exit 1
    fi

    case "${2:-}" in
        -f|--follow) exec tail -n 50 -f "$LATEST" ;;
        -a|--all)    exec cat "$LATEST" ;;
        -l|--list)   ls -1t "$LOG_DIR"/prod-*.log 2>/dev/null || echo "No completed runs in $LOG_DIR."; exit 0 ;;
        "")
            echo "== $LOG_DIR/$(basename "$(readlink "$LATEST" 2>/dev/null || echo "$LATEST")") — last 200 lines =="
            exec tail -n 200 "$LATEST"
            ;;
        *) echo "Unknown option '$2'. Use -f (follow), -a (all) or -l (list)." >&2; exit 2 ;;
    esac
fi

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

# --- Keep a log of this run ------------------------------------------------
# gunicorn's access log, its error log and the application logger all write to
# the console, and in production that console is an ssh session that will not
# still be open when somebody reports the game broke an hour ago. So every
# production run also lands in a file. It is not opt-in: there is no useful
# version of "I would have liked logs of that run".
#
# One file per run, named for when it started, plus a 'latest.log' symlink that
# 'run_all.sh logs' follows. Old runs are pruned so this never grows unbounded.
RUN_LOG=""
if mkdir -p "$LOG_DIR" 2>/dev/null; then
    CANDIDATE="$LOG_DIR/prod-$(date +%Y%m%d-%H%M%S).log"
    if : > "$CANDIDATE" 2>/dev/null; then
        RUN_LOG="$CANDIDATE"
        ln -sfn "$(basename "$RUN_LOG")" "$LOG_DIR/latest.log" 2>/dev/null

        # Port 80 means this was probably started with sudo. Hand the logs back
        # to the account that will run 'run_all.sh logs' afterwards, so reading
        # them does not also need root.
        [ -n "${SUDO_USER:-}" ] && chown -R "$SUDO_USER" "$LOG_DIR" 2>/dev/null

        if [[ "$LOG_KEEP" =~ ^[0-9]+$ ]] && [ "$LOG_KEEP" -gt 0 ]; then
            ls -1t "$LOG_DIR"/prod-*.log 2>/dev/null \
                | tail -n "+$((LOG_KEEP + 1))" \
                | while IFS= read -r stale; do rm -f "$stale"; done
        fi
    fi
fi
if [ -z "$RUN_LOG" ]; then
    echo "Warning: cannot write to $LOG_DIR. This run is logged to the console only." >&2
fi

cat <<BANNER

  Finding Friends is starting on http://${ADDRESS}${DISPLAY_PORT}

  Share that address. One player creates a game and passes the code to the
  rest; five players minimum.

  The page, the API and the websocket are all on this one port, so nothing
  else needs opening. If players outside cannot reach it, check the firewall
  (on a DigitalOcean droplet: 'ufw allow ${PORT}').

  Anyone with the address can join a game. Stop the server with Ctrl+C.

BANNER

if [ -n "$RUN_LOG" ]; then
    cat <<BANNER
  Logging this run to $RUN_LOG

    bash run_all.sh logs        the last 200 lines
    bash run_all.sh logs -f     follow it live, from another terminal
    bash run_all.sh logs -l     every run still kept (last $LOG_KEEP)

BANNER
fi

# Python block-buffers stdout when it is a pipe rather than a terminal. The
# logging handlers flush every record, so this is only for anything that
# reaches stdout by some other route.
export PYTHONUNBUFFERED=1

GUNICORN=(
    "$VENV/bin/gunicorn"
    --worker-class gthread
    --workers 1
    --threads 100
    -b "0.0.0.0:$PORT"
    --access-logfile -
    Main:app
)

if [ -z "$RUN_LOG" ]; then
    exec "${GUNICORN[@]}"
fi

# tee rather than gunicorn's --log-file, so the terminal still shows the server
# live while the file collects the same thing. Not exec'd: gunicorn runs as a
# child so the trap can forward Ctrl+C, and the TERM from `kill` on a nohup'd
# run, on to it instead of leaving it orphaned.
#
# The plumbing is a named pipe rather than the obvious `> >(tee ...)`, because
# process substitution does not exist when bash is running in POSIX mode, and
# it fails as a syntax error at this line rather than as a missing feature.
LOG_FIFO="$LOG_DIR/.run-$$.fifo"
rm -f "$LOG_FIFO"
if ! mkfifo "$LOG_FIFO" 2>/dev/null; then
    echo "Warning: cannot create a pipe in $LOG_DIR. Logging to the console only." >&2
    exec "${GUNICORN[@]}"
fi

tee -a "$RUN_LOG" < "$LOG_FIFO" &
TEE_PID=$!
# Hold the write end open here first. That unblocks tee, and it means the pipe
# can be unlinked immediately — the open descriptors keep working, and no stale
# fifo is left in the log directory if the server is killed.
exec 3> "$LOG_FIFO"
rm -f "$LOG_FIFO"

"${GUNICORN[@]}" >&3 2>&1 &
GUNICORN_PID=$!
# Drop this shell's copy, so tee sees end-of-file when gunicorn exits.
exec 3>&-

trap 'kill -TERM "$GUNICORN_PID" 2>/dev/null' INT TERM

while :; do
    wait "$GUNICORN_PID"
    STATUS=$?
    # A status above 128 is ambiguous: either gunicorn died from a signal, or a
    # signal we trapped merely interrupted the wait. Only the second case leaves
    # the process alive, and only that case should go round again.
    if [ "$STATUS" -le 128 ] || ! kill -0 "$GUNICORN_PID" 2>/dev/null; then
        break
    fi
done
trap - INT TERM

# Let tee finish writing what gunicorn produced on its way out.
wait "$TEE_PID" 2>/dev/null

echo "Server stopped. This run is in $RUN_LOG"
exit "$STATUS"
