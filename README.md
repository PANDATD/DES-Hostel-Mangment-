# Hostel Management — Normalized Standalone Build

A Flask hostel-management application with normalized relational data, full CRUD workflows for the V1 modules, secure password reset, geography-based attendance, Alembic migrations, and automated tests.

## Included features

- Admin and student authentication
- Secure forgot-password/reset-password flow
- Students: create, read, update, delete
- Blocks: create, read, update, delete
- Rooms: create, read, update, delete
- Room allocations: create/transfer, read history, end, delete ended history
- Complaints: student create/read/edit/delete while open; admin update/edit/delete
- Fees: create, read, update, delete
- Fee payments: create, read, update, delete
- Attendance: student geo check-in; admin read/update/delete
- Attendance geofences: create, read, update, delete
- Normalized master data: courses, academic years, complaint categories, fee types, payment methods
- Admin and student dashboards

## Database normalization

Repeated business values are no longer stored as unconstrained text in transactional tables.

Normalized lookup tables:

- `courses`
- `academic_years`
- `complaint_categories`
- `fee_types`
- `payment_methods`

Transactional tables reference them with foreign keys:

- `student_profiles.course_id -> courses.id`
- `student_profiles.academic_year_id -> academic_years.id`
- `complaints.category_id -> complaint_categories.id`
- `fees.academic_year_id -> academic_years.id`
- `fees.fee_type_id -> fee_types.id`
- `fee_payments.payment_method_id -> payment_methods.id`

The schema also contains uniqueness constraints, domain checks, indexes, one-current-room-allocation enforcement, one-attendance-per-student-per-day enforcement, and SQLite foreign-key checking.

## Password reset

Password-reset tokens are:

- generated with cryptographic randomness;
- stored only as SHA-256 hashes;
- time limited;
- single use;
- invalidated when a newer token is requested or a token is consumed.

The response to a forgot-password request is intentionally generic so the page does not reveal whether an email address exists.

For local development, when SMTP is not configured and `PASSWORD_RESET_SHOW_LINK=1`, the reset link is shown on screen so the standalone build remains testable. In production, configure SMTP and set `PASSWORD_RESET_SHOW_LINK=0`.

## Requirements

- Python 3.12
- SQLite for the bundled/local setup

## Run the bundled standalone database

The ZIP includes an already migrated `instance/hostel.db` containing the data that was supplied with the original project.

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m flask --app run.py db upgrade
python -m flask --app run.py doctor
python -m flask --app run.py run --debug
```

Open the local Flask address shown in the terminal.

## Create a fresh database instead

Delete or move `instance/hostel.db`, then run:

```bash
python -m flask --app run.py db upgrade
python -m flask --app run.py seed-demo
python -m flask --app run.py run --debug
```

`seed-demo` creates normalized master data, Block 2, 97 rooms, 106 demo students, room allocations, an admin, and one attendance geofence.

## Demo credentials

Admin:

```text
admin@example.com
Admin@123
```

Seeded students:

```text
b2student001@example.com
...
b2student106@example.com

Password: Student@123
```

These are development credentials. Change them before any real deployment.

## Password-reset email configuration

Configure these values in `.env` for SMTP delivery:

```dotenv
PASSWORD_RESET_TTL_MINUTES=30
PASSWORD_RESET_SHOW_LINK=0
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=user@example.com
MAIL_PASSWORD=change-me
MAIL_USE_TLS=1
MAIL_DEFAULT_SENDER=user@example.com
MAIL_TIMEOUT=10
```

The application uses Python's standard `smtplib`, so no additional email package is required.

## Attendance configuration

The browser sends latitude, longitude, and reported accuracy. The server calculates Haversine distance and validates the active geofence, GPS accuracy, time window, student status, and duplicate attendance.

For demo seeding, configure:

```dotenv
HOSTEL_LAT=18.5204
HOSTEL_LNG=73.8567
HOSTEL_RADIUS_METRES=150
MAX_GPS_ACCURACY_METRES=100
```

Replace demo coordinates with the real hostel coordinates before real use.

## Database migration

Existing databases at revision `0001_v1_schema` are upgraded by:

```bash
python -m flask --app run.py db upgrade
```

Revision `0002_normalized_crud_reset` migrates existing course/year/category/fee/payment values into lookup tables and preserves existing records through foreign-key mappings.

Check integrity after migration:

```bash
python -m flask --app run.py doctor
```

`doctor` reports the database path, tables, SQLite foreign-key state, journal mode, and foreign-key violations.

## Tests

Install the development group with `uv`, or install `pytest` separately, then run:

```bash
pytest -q
ruff check app tests migrations/versions/0002_normalized_crud_reset.py
```

The supplied test suite covers login, password reset, student CRUD, block/room CRUD, allocation lifecycle, complaint CRUD/admin workflow, fee/payment CRUD, normalized master-data CRUD, attendance duplicate protection/admin CRUD, geofence CRUD, and Haversine calculation.

## Deletion behaviour

Some delete operations are intentionally destructive:

- deleting a student removes records owned by that student, including complaints, attendance, allocations, fees, and payments;
- deleting a fee also deletes its payments;
- a block cannot be deleted while it still contains rooms;
- a room cannot be deleted while allocation history exists;
- a referenced master-data value cannot be deleted and should be deactivated instead;
- a geofence with attendance history cannot be deleted.

Use database backups before bulk administrative changes.

## Deployment note

SQLite is suitable for local and small single-instance deployments. A Vercel/serverless filesystem is not durable storage for a SQLite database. For production hosting, use durable database storage and production-grade secrets, SMTP, TLS, backups, and logging.
# DES-Hostel-Mangment-
