IF NOT EXIST images mkdir images
IF NOT EXIST images\crop mkdir images\crop
py -m venv venv
venv\scripts\python -m pip install -r requirements.txt