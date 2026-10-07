#!/bin/sh
set -e

echo "Running database migrations..."
python3 -m flask --app run.py db upgrade

echo "Database migrations completed."
