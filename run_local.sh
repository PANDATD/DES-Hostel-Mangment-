#!/usr/bin/env sh
set -eu
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
fi
.venv/bin/python -m flask --app run.py db upgrade
.venv/bin/python -m flask --app run.py doctor
exec .venv/bin/python -m flask --app run.py run --debug
