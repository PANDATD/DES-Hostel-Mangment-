@echo off
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)
.venv\Scripts\python.exe -m flask --app run.py db upgrade
.venv\Scripts\python.exe -m flask --app run.py doctor
.venv\Scripts\python.exe -m flask --app run.py run --debug
