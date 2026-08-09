echo $PWD

# Clear old database
bash "$(dirname "$0")/clear_db.sh"

if [ "$1" = "--recreate-venv" ]; then
    echo "Deleting and recreating backend_venv..."
    rm -rf backend_venv
    python -m venv backend_venv
    echo "Virtual environment recreated."
fi

source backend_venv/bin/activate
# Dev deps too: this script runs the test suite before serving.
pip install -r requirement.txt -r requirement-dev.txt
pytest
# gthread, not eventlet: the app uses Flask-SocketIO's threading async_mode.
# --workers must stay 1 — broadcast_player_views reads an in-process dict, so a
# second worker would silently miss half the players.
gunicorn --worker-class gthread -b 127.0.0.1:5050 --workers 1 --threads 100 Main:app --log-level debug
