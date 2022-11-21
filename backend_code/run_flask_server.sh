echo $PWD
source backend_venv/bin/activate
pip install -r requirement.txt
pytest 
flask --app Main.py run


