from __future__ import annotations

import os
from datetime import date, time
from decimal import Decimal

import click
from flask import Flask
from flask.cli import with_appcontext
from sqlalchemy import inspect, or_, select

from app.extensions import db
from app.models import (
    AcademicYear,
    AttendanceGeofence,
    Block,
    ComplaintCategory,
    Course,
    FeeType,
    PaymentMethod,
    ResidentStatus,
    Role,
    Room,
    RoomAllocation,
    StudentProfile,
    User,
)

DOUBLE_ROOMS = {70, 80, 90, 100, 110, 120, 130, 140, 150}
FIRST_NAMES = [
    "Aarav",
    "Vivaan",
    "Aditya",
    "Arjun",
    "Reyansh",
    "Krishna",
    "Ishaan",
    "Shaurya",
    "Atharv",
    "Dhruv",
    "Kabir",
    "Rohan",
    "Rahul",
    "Siddharth",
    "Kunal",
    "Nikhil",
    "Manav",
    "Yash",
    "Harsh",
    "Akash",
    "Pranav",
    "Omkar",
    "Tejas",
    "Sanket",
    "Abhishek",
    "Ritesh",
    "Saurabh",
    "Aniket",
    "Ganesh",
    "Swapnil",
    "Shubham",
    "Vivek",
]
LAST_NAMES = [
    "Sharma",
    "Patil",
    "Deshmukh",
    "Kulkarni",
    "Jadhav",
    "Joshi",
    "Shinde",
    "Pawar",
    "Kadam",
    "More",
    "Chavan",
    "Gaikwad",
    "Mane",
    "Sawant",
    "Nair",
    "Iyer",
    "Reddy",
    "Rao",
    "Verma",
    "Gupta",
    "Singh",
    "Yadav",
    "Mishra",
    "Tiwari",
]
COURSES = ["B.Tech CSE", "B.Tech IT", "B.Sc", "B.Com", "BA", "BBA"]
COMPLAINT_CATEGORIES = [
    ("ELECTRICAL", "Electrical"),
    ("PLUMBING", "Plumbing"),
    ("CLEANING", "Cleaning"),
    ("FURNITURE", "Furniture"),
    ("MESS", "Mess / Food"),
    ("SECURITY", "Security"),
    ("OTHER", "Other"),
]
PAYMENT_METHODS = [("CASH", "Cash"), ("UPI", "UPI"), ("BANK", "Bank"), ("OTHER", "Other")]


def _get_or_create_ref(model, code: str, name: str):
    item = db.session.scalar(select(model).where(or_(model.code == code, model.name == name)))
    if item is None:
        item = model(code=code, name=name, active=True)
        db.session.add(item)
    else:
        item.code = code
        item.name = name
        item.active = True
    db.session.flush()
    return item


def _seed_reference_data() -> dict[str, object]:
    academic_year = _get_or_create_ref(AcademicYear, "2026-27", "2026-27")
    course_map = {
        name: _get_or_create_ref(Course, name.upper().replace(" ", "-").replace(".", ""), name)
        for name in COURSES
    }
    for code, name in COMPLAINT_CATEGORIES:
        _get_or_create_ref(ComplaintCategory, code, name)
    hostel_fee = _get_or_create_ref(FeeType, "HOSTEL", "Hostel Fee")
    for code, name in PAYMENT_METHODS:
        _get_or_create_ref(PaymentMethod, code, name)
    return {"academic_year": academic_year, "courses": course_map, "hostel_fee": hostel_fee}


def _seed_admin() -> User:
    admin = db.session.scalar(select(User).where(User.email == "admin@example.com"))
    if admin is None:
        admin = User(username="admin", email="admin@example.com", role=Role.ADMIN, active=True)
        db.session.add(admin)
    admin.username = "admin"
    admin.role = Role.ADMIN
    admin.active = True
    admin.set_password("Admin@123")
    db.session.flush()
    return admin


def _seed_block_and_rooms() -> dict[int, Room]:
    block = db.session.scalar(select(Block).where(Block.code == "BLOCK-2"))
    if block is None:
        block = Block(code="BLOCK-2", name="Block 2", active=True)
        db.session.add(block)
    block.name = "Block 2"
    block.active = True
    db.session.flush()

    room_map: dict[int, Room] = {}
    for number in range(60, 157):
        room = db.session.scalar(
            select(Room).where(Room.block_id == block.id, Room.number == str(number))
        )
        if room is None:
            room = Room(block_id=block.id, number=str(number))
            db.session.add(room)
        room.floor = 0 if number <= 108 else 1
        room.capacity = 2 if number in DOUBLE_ROOMS else 1
        room.active = True
        room_map[number] = room
    db.session.flush()
    return room_map


def _seed_geofence() -> None:
    geofence = db.session.scalar(
        select(AttendanceGeofence).where(AttendanceGeofence.active.is_(True))
    )
    if geofence is None:
        geofence = AttendanceGeofence(
            name="Block 2 Hostel Geofence",
            latitude=Decimal(os.getenv("HOSTEL_LAT", "18.5204000")),
            longitude=Decimal(os.getenv("HOSTEL_LNG", "73.8567000")),
            radius_metres=Decimal(os.getenv("HOSTEL_RADIUS_METRES", "150")),
            max_accuracy_metres=Decimal(os.getenv("MAX_GPS_ACCURACY_METRES", "100")),
            check_in_start=time(18, 0),
            check_in_end=time(23, 59),
            late_after=time(22, 0),
            timezone="Asia/Kolkata",
            active=True,
        )
        db.session.add(geofence)


def _student_slots() -> list[tuple[int, str]]:
    slots: list[tuple[int, str]] = []
    for number in range(60, 157):
        capacity = 2 if number in DOUBLE_ROOMS else 1
        for bed in range(1, capacity + 1):
            slots.append((number, str(bed)))
    return slots


def _seed_students(admin: User, room_map: dict[int, Room], refs: dict[str, object]) -> None:
    academic_year = refs["academic_year"]
    courses = refs["courses"]
    for index, (room_no, bed) in enumerate(_student_slots(), start=1):
        email = f"b2student{index:03d}@example.com"
        username = f"b2student{index:03d}"
        student_code = f"B2-{index:03d}"

        user = db.session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(username=username, email=email, role=Role.STUDENT, active=True)
            db.session.add(user)
        user.username = username
        user.role = Role.STUDENT
        user.active = True
        user.set_password("Student@123")
        db.session.flush()

        profile = db.session.scalar(
            select(StudentProfile).where(StudentProfile.student_code == student_code)
        )
        if profile is None:
            profile = StudentProfile(user_id=user.id, student_code=student_code, full_name="")
            db.session.add(profile)
        profile.user_id = user.id
        profile.full_name = (
            f"{FIRST_NAMES[(index - 1) % len(FIRST_NAMES)]} "
            f"{LAST_NAMES[((index - 1) * 3) % len(LAST_NAMES)]}"
        )
        profile.phone = f"9{index:09d}"[-10:]
        profile.course_id = courses[COURSES[(index - 1) % len(COURSES)]].id
        profile.academic_year_id = academic_year.id
        profile.resident_status = ResidentStatus.ACTIVE
        profile.joined_on = date.today()
        db.session.flush()

        current = db.session.scalar(
            select(RoomAllocation).where(
                RoomAllocation.student_id == profile.id,
                RoomAllocation.ended_on.is_(None),
            )
        )
        target = room_map[room_no]
        if current and current.room_id == target.id and current.bed_label == bed:
            continue
        if current:
            current.ended_on = date.today()
        db.session.add(
            RoomAllocation(
                student_id=profile.id,
                room_id=target.id,
                bed_label=bed,
                started_on=date.today(),
                allocated_by_user_id=admin.id,
            )
        )
        db.session.flush()


@click.command("seed-demo")
@with_appcontext
def seed_demo() -> None:
    """Seed normalized master data, Block 2, 106 students and a geofence."""
    refs = _seed_reference_data()
    admin = _seed_admin()
    room_map = _seed_block_and_rooms()
    _seed_geofence()
    _seed_students(admin, room_map, refs)
    db.session.commit()
    click.echo("Demo data ready.")
    click.echo("Admin: admin@example.com / Admin@123")
    click.echo("Students: b2student001@example.com ... b2student106@example.com / Student@123")
    click.echo("IMPORTANT: update hostel geofence coordinates before real attendance use.")


@click.command("reset-admin-password")
@click.option("--email", default="admin@example.com", show_default=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@with_appcontext
def reset_admin_password(email: str, password: str) -> None:
    """Reset an existing admin account password without storing it in source control."""
    admin = db.session.scalar(
        select(User).where(User.email == email.strip().lower(), User.role == Role.ADMIN)
    )
    if admin is None:
        raise click.ClickException(f"No admin account found for {email}.")
    if not password:
        raise click.ClickException("Password must not be empty.")

    admin.set_password(password)
    admin.active = True
    db.session.commit()
    click.echo(f"Admin password reset successfully for {admin.email}.")


@click.command("seed-master-data")
@with_appcontext
def seed_master_data() -> None:
    """Create/update the normalized lookup tables without creating demo students."""
    _seed_reference_data()
    db.session.commit()
    click.echo("Master data ready.")


@click.command("doctor")
@with_appcontext
def doctor() -> None:
    """Show the active database and basic schema health."""
    engine = db.engine
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    click.echo(f"Database: {engine.url.render_as_string(hide_password=True)}")
    click.echo(f"Tables ({len(tables)}): {', '.join(sorted(tables))}")
    if engine.dialect.name == "sqlite":
        with engine.connect() as connection:
            fk = connection.exec_driver_sql("PRAGMA foreign_keys").scalar()
            journal = connection.exec_driver_sql("PRAGMA journal_mode").scalar()
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        click.echo(f"SQLite foreign_keys: {fk}")
        click.echo(f"SQLite journal_mode: {journal}")
        click.echo(f"Foreign-key violations: {len(violations)}")


def register_commands(app: Flask) -> None:
    app.cli.add_command(seed_demo)
    app.cli.add_command(seed_master_data)
    app.cli.add_command(reset_admin_password)
    app.cli.add_command(doctor)
