echo $PWD

if [ "$1" = "--recreate-venv" ]; then
    echo "Deleting and recreating backend_venv..."
    rm -rf backend_venv
    python -m venv backend_venv
    echo "Virtual environment recreated."
fi

source backend_venv/bin/activate
pip install -r requirement.txt
pytest
gunicorn -k eventlet -b 127.0.0.1:5000 --workers 1 --threads 100 Main:app --log-level debug
