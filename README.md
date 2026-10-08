# Hostel Management

A Flask hostel-management application with relational data models, CRUD workflows, authentication, password reset, attendance, database migrations, and tests.

## Main areas

- Admin and student authentication
- Student, block, room and allocation management
- Complaints
- Fees and payments
- Attendance and geofencing
- Normalized master data
- Alembic migrations

## Requirements

- Python 3.12
- SQLite for local development
- PostgreSQL for deployment where configured
- Psycopg 3 for PostgreSQL connectivity

## Local setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m flask --app run.py db upgrade
python -m flask --app run.py doctor
python -m flask --app run.py run --debug
```

## Database

Database schema changes are managed through Flask-Migrate/Alembic. Run migrations before using a fresh database.

## Authentication and secrets

Passwords and reset tokens are handled by the application. Development credentials or reset links must not be reused for a real deployment. Keep database credentials, SMTP credentials, and secret keys outside Git.

## Tests

```bash
pytest -q
ruff check app tests migrations/versions
```

## Project work

Tejas Dixit — https://tejasdixit.in
