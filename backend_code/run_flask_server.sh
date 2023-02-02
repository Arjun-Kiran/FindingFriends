echo $PWD
source backend_venv/bin/activate
pip install -r requirement.txt
pytest 
gunicorn -b 127.0.0.1:5000 --workers 4 --threads 100 Main:app
