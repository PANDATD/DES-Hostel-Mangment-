from __future__ import annotations

from datetime import date

from app.extensions import db
from app.models import (
    Block,
    Complaint,
    Course,
    Fee,
    FeePayment,
    Room,
    RoomAllocation,
    StudentProfile,
)
from tests.conftest import login_admin, login_student


def test_student_crud(app, client, seeded):
    login_admin(client)
    response = client.post(
        "/admin/students",
        data={
            "username": "newstudent",
            "email": "new@example.com",
            "password": "Student@123",
            "student_code": "S002",
            "full_name": "New Student",
            "phone": "9999999999",
            "course_id": seeded["course_id"],
            "academic_year_id": seeded["year_id"],
        },
        follow_redirects=True,
    )
    assert b"Student created" in response.data
    with app.app_context():
        student = db.session.query(StudentProfile).filter_by(student_code="S002").one()
        student_id = student.id
    response = client.post(
        f"/admin/students/{student_id}/edit",
        data={
            "username": "newstudent",
            "email": "new@example.com",
            "student_code": "S002",
            "full_name": "Updated Student",
            "course_id": seeded["course_id"],
            "academic_year_id": seeded["year_id"],
            "resident_status": "ACTIVE",
            "active": "y",
        },
        follow_redirects=True,
    )
    assert b"Student updated" in response.data
    response = client.post(f"/admin/students/{student_id}/delete", data={}, follow_redirects=True)
    assert b"Student and owned records deleted" in response.data
    with app.app_context():
        assert db.session.get(StudentProfile, student_id) is None


def test_block_room_and_allocation_crud(app, client, seeded):
    login_admin(client)
    response = client.post(
        "/admin/blocks",
        data={"code": "B3", "name": "Block 3", "active": "y"},
        follow_redirects=True,
    )
    assert b"Block created" in response.data
    with app.app_context():
        block = db.session.query(Block).filter_by(code="B3").one()
        block_id = block.id
    response = client.post(
        "/admin/rooms/create",
        data={"block_id": block_id, "number": "301", "floor": 2, "capacity": 2, "active": "y"},
        follow_redirects=True,
    )
    assert b"Room created" in response.data
    with app.app_context():
        room = db.session.query(Room).filter_by(block_id=block_id, number="301").one()
        room_id = room.id
    response = client.post(
        f"/admin/rooms/{room_id}/edit",
        data={"block_id": block_id, "number": "302", "floor": 2, "capacity": 3, "active": "y"},
        follow_redirects=True,
    )
    assert b"Room updated" in response.data
    response = client.post(
        "/admin/rooms",
        data={"student_id": seeded["student_id"], "room_id": room_id, "bed_label": "A"},
        follow_redirects=True,
    )
    assert b"Room allocation saved" in response.data
    with app.app_context():
        allocation = (
            db.session.query(RoomAllocation)
            .filter_by(student_id=seeded["student_id"], ended_on=None)
            .one()
        )
        allocation_id = allocation.id
    assert (
        b"ended"
        in client.post(
            f"/admin/allocations/{allocation_id}/end", data={}, follow_redirects=True
        ).data
    )
    assert (
        b"history deleted"
        in client.post(
            f"/admin/allocations/{allocation_id}/delete", data={}, follow_redirects=True
        ).data
    )
    assert (
        b"Room deleted"
        in client.post(f"/admin/rooms/{room_id}/delete", data={}, follow_redirects=True).data
    )
    assert (
        b"Block deleted"
        in client.post(f"/admin/blocks/{block_id}/delete", data={}, follow_redirects=True).data
    )


def test_complaint_crud_and_admin_update(app, client, seeded):
    login_student(client)
    response = client.post(
        "/student/complaints",
        data={
            "category_id": seeded["category_id"],
            "subject": "Tap leaking",
            "description": "Tap has leaked since morning.",
        },
        follow_redirects=True,
    )
    assert b"Complaint submitted" in response.data
    with app.app_context():
        complaint = db.session.query(Complaint).filter_by(student_id=seeded["student_id"]).one()
        complaint_id = complaint.id
    response = client.post(
        f"/student/complaints/{complaint_id}/edit",
        data={
            "category_id": seeded["category_id"],
            "subject": "Tap still leaking",
            "description": "Tap is still leaking badly.",
        },
        follow_redirects=True,
    )
    assert b"Complaint updated" in response.data
    client.post("/logout", data={})
    login_admin(client)
    response = client.post(
        f"/admin/complaints/{complaint_id}",
        data={"status": "IN_PROGRESS", "admin_notes": "Assigned"},
        follow_redirects=True,
    )
    assert b"Complaint updated" in response.data
    response = client.post(
        f"/admin/complaints/{complaint_id}/delete", data={}, follow_redirects=True
    )
    assert b"Complaint deleted" in response.data


def test_fee_and_payment_crud(app, client, seeded):
    login_admin(client)
    response = client.post(
        "/admin/fees",
        data={
            "student_id": seeded["student_id"],
            "academic_year_id": seeded["year_id"],
            "fee_type_id": seeded["fee_type_id"],
            "amount_due": "1000.00",
            "due_date": "2026-10-01",
        },
        follow_redirects=True,
    )
    assert b"Fee record created" in response.data
    with app.app_context():
        fee = db.session.query(Fee).filter_by(student_id=seeded["student_id"]).one()
        fee_id = fee.id
    response = client.post(
        f"/admin/fees/{fee_id}/payment",
        data={
            "amount": "250.00",
            "paid_on": date.today().isoformat(),
            "payment_method_id": seeded["payment_method_id"],
        },
        follow_redirects=True,
    )
    assert b"Payment recorded" in response.data
    with app.app_context():
        payment = db.session.query(FeePayment).filter_by(fee_id=fee_id).one()
        payment_id = payment.id
    response = client.post(
        f"/admin/payments/{payment_id}/edit",
        data={
            "amount": "300.00",
            "paid_on": date.today().isoformat(),
            "payment_method_id": seeded["payment_method_id"],
        },
        follow_redirects=True,
    )
    assert b"Payment updated" in response.data
    assert (
        b"Payment deleted"
        in client.post(f"/admin/payments/{payment_id}/delete", data={}, follow_redirects=True).data
    )
    response = client.post(
        f"/admin/fees/{fee_id}/edit",
        data={
            "student_id": seeded["student_id"],
            "academic_year_id": seeded["year_id"],
            "fee_type_id": seeded["fee_type_id"],
            "amount_due": "1200.00",
            "due_date": "2026-10-15",
        },
        follow_redirects=True,
    )
    assert b"Fee updated" in response.data
    assert (
        b"Fee and its payment records deleted"
        in client.post(f"/admin/fees/{fee_id}/delete", data={}, follow_redirects=True).data
    )


def test_master_data_crud(app, client, seeded):
    login_admin(client)
    response = client.post(
        "/admin/master-data/courses",
        data={"code": "BCA", "name": "BCA", "active": "y"},
        follow_redirects=True,
    )
    assert b"created" in response.data
    with app.app_context():
        course = db.session.query(Course).filter_by(code="BCA").one()
        course_id = course.id
    response = client.post(
        f"/admin/master-data/courses/{course_id}/edit",
        data={"code": "BCA", "name": "Bachelor of Computer Applications", "active": "y"},
        follow_redirects=True,
    )
    assert b"updated" in response.data
    response = client.post(
        f"/admin/master-data/courses/{course_id}/delete", data={}, follow_redirects=True
    )
    assert b"deleted" in response.data
