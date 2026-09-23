from __future__ import annotations

from decimal import Decimal

import pytest

from app import create_app
from app.config import Config
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
    StudentProfile,
    User,
)


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    PASSWORD_RESET_SHOW_LINK = True
    PASSWORD_RESET_TTL_MINUTES = 30


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seeded(app):
    with app.app_context():
        course = Course(code="BTECH-CSE", name="B.Tech CSE", active=True)
        year = AcademicYear(code="2026-27", name="2026-27", active=True)
        category = ComplaintCategory(code="PLUMBING", name="Plumbing", active=True)
        fee_type = FeeType(code="HOSTEL", name="Hostel Fee", active=True)
        payment_method = PaymentMethod(code="UPI", name="UPI", active=True)
        block = Block(code="B2", name="Block 2", active=True)
        db.session.add_all([course, year, category, fee_type, payment_method, block])
        db.session.flush()
        room = Room(block_id=block.id, number="101", floor=0, capacity=2, active=True)
        admin = User(username="admin", email="admin@example.com", role=Role.ADMIN, active=True)
        admin.set_password("Admin@123")
        student_user = User(
            username="student", email="student@example.com", role=Role.STUDENT, active=True
        )
        student_user.set_password("Student@123")
        db.session.add_all([room, admin, student_user])
        db.session.flush()
        student = StudentProfile(
            user_id=student_user.id,
            student_code="S001",
            full_name="Test Student",
            course_id=course.id,
            academic_year_id=year.id,
            resident_status=ResidentStatus.ACTIVE,
        )
        geofence = AttendanceGeofence(
            name="Hostel",
            latitude=Decimal("18.5204000"),
            longitude=Decimal("73.8567000"),
            radius_metres=Decimal("200.00"),
            max_accuracy_metres=Decimal("100.00"),
            check_in_start=None,
            check_in_end=None,
            late_after=None,
            timezone="Asia/Kolkata",
            active=True,
        )
        db.session.add_all([student, geofence])
        db.session.commit()
        return {
            "course_id": course.id,
            "year_id": year.id,
            "category_id": category.id,
            "fee_type_id": fee_type.id,
            "payment_method_id": payment_method.id,
            "block_id": block.id,
            "room_id": room.id,
            "admin_id": admin.id,
            "student_id": student.id,
            "student_user_id": student_user.id,
            "geofence_id": geofence.id,
        }


def test_config_defaults_when_numeric_env_values_are_empty(monkeypatch):
    import importlib

    monkeypatch.setenv("PASSWORD_RESET_TTL_MINUTES", "")
    monkeypatch.setenv("MAIL_PORT", "")
    monkeypatch.setenv("MAIL_TIMEOUT", "")

    import app.config as config_module

    importlib.reload(config_module)

    assert config_module.Config.PASSWORD_RESET_TTL_MINUTES == 30
    assert config_module.Config.MAIL_PORT == 587
    assert config_module.Config.MAIL_TIMEOUT == 10.0

    monkeypatch.delenv("PASSWORD_RESET_TTL_MINUTES")
    monkeypatch.delenv("MAIL_PORT")
    monkeypatch.delenv("MAIL_TIMEOUT")
    importlib.reload(config_module)


def login_admin(client):
    return client.post("/login", data={"login": "admin@example.com", "password": "Admin@123"})


def login_student(client):
    return client.post("/login", data={"login": "student@example.com", "password": "Student@123"})
