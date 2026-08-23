#!/bin/bash
echo $PWD

# Resolve the Python version pinned in .python-version, if pyenv is installed.
# Without this the venv gets built with whatever python is on PATH, which may
# not be the version the project is tested against.
# python3 as the default: plain `python` does not exist on a stock macOS.
PYTHON=$(command -v python3 || command -v python)
if command -v pyenv >/dev/null 2>&1; then
    # version-file-read, not version-name: the latter fails outright when the
    # pinned version is not installed, which is the case we want to report.
    PINNED=$(pyenv version-file-read "$(pyenv version-file)" 2>/dev/null)
    if [ -n "$PINNED" ] && PREFIX=$(pyenv prefix "$PINNED" 2>/dev/null); then
        PYTHON="$PREFIX/bin/python3"
        pin_resolved=1
        echo "Using Python $PINNED via pyenv."
    else
        echo "Warning: pinned Python ${PINNED:-(unset)} is not installed (try 'pyenv install $PINNED')."
        echo "Continuing with $("$PYTHON" -V 2>&1)."
    fi
fi

# Clear old database
bash "$(dirname "$0")/clear_db.sh"

if [ "$1" = "--recreate-venv" ]; then
    echo "Deleting backend_venv..."
    rm -rf backend_venv
fi

# Also covers a fresh clone, where backend_venv does not exist yet.
if [ ! -d backend_venv ]; then
    echo "Creating backend_venv..."
    "$PYTHON" -m venv backend_venv
fi

# A venv built against an older Python keeps working silently, so say something.
# Only meaningful when pyenv resolved the pin; without it there is no
# authoritative version to compare the venv against.
if [ -n "$pin_resolved" ]; then
    venv_version=$(sed -n 's/^version *= *//p' backend_venv/pyvenv.cfg 2>/dev/null)
    if [ -n "$venv_version" ] && [ "$venv_version" != "$PINNED" ]; then
        echo "Warning: backend_venv is Python $venv_version but $PINNED is pinned."
        echo "Rebuild it with: bash run_flask_server.sh --recreate-venv"
    fi
fi

source backend_venv/bin/activate
# Dev deps too: this script runs the test suite before serving.
pip install -r requirement.txt -r requirement-dev.txt
pytest
# gthread, not eventlet: the app uses Flask-SocketIO's threading async_mode.
# --workers must stay 1 — broadcast_player_views reads an in-process dict, so a
# second worker would silently miss half the players.
gunicorn --worker-class gthread -b 127.0.0.1:5050 --workers 1 --threads 100 Main:app --log-level debug
