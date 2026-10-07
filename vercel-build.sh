#!/bin/sh
set -e

# Use Neon's direct connection for migrations when available.
# Fall back to DATABASE_URL so manual Vercel environment variables also work.
if [ -n "${DATABASE_URL_UNPOOLED:-}" ]; then
  export DATABASE_URL="$DATABASE_URL_UNPOOLED"
fi

echo "Running database migrations..."
python3 -m flask --app run.py db upgrade

echo "Database migrations completed."
