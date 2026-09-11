from __future__ import annotations

from datetime import date

from app.extensions import db
from app.models import AttendanceGeofence, AttendanceRecord
from tests.conftest import login_admin, login_student


def test_attendance_create_duplicate_edit_delete(app, client, seeded):
    login_student(client)
    payload = {"latitude": "18.5204000", "longitude": "73.8567000", "accuracy": "10"}
    response = client.post("/student/attendance", data=payload, follow_redirects=True)
    assert b"Attendance marked successfully" in response.data
    response = client.post("/student/attendance", data=payload, follow_redirects=True)
    assert b"Attendance is already marked" in response.data
    with app.app_context():
        record = db.session.query(AttendanceRecord).filter_by(student_id=seeded["student_id"]).one()
        record_id = record.id
    client.post("/logout", data={})
    login_admin(client)
    response = client.post(
        f"/admin/attendance/{record_id}/edit",
        data={"attendance_date": date.today().isoformat(), "is_late": "y"},
        follow_redirects=True,
    )
    assert b"Attendance record updated" in response.data
    response = client.post(f"/admin/attendance/{record_id}/delete", data={}, follow_redirects=True)
    assert b"Attendance record deleted" in response.data


def test_geofence_crud(app, client, seeded):
    login_admin(client)
    response = client.post(
        "/admin/geofences/create",
        data={
            "name": "Annex",
            "latitude": "18.5205000",
            "longitude": "73.8568000",
            "radius_metres": "100",
            "max_accuracy_metres": "50",
            "timezone": "Asia/Kolkata",
        },
        follow_redirects=True,
    )
    assert b"Geofence created" in response.data
    with app.app_context():
        g = db.session.query(AttendanceGeofence).filter_by(name="Annex").one()
        gid = g.id
    response = client.post(
        f"/admin/geofences/{gid}/edit",
        data={
            "name": "Annex Updated",
            "latitude": "18.5205000",
            "longitude": "73.8568000",
            "radius_metres": "120",
            "max_accuracy_metres": "60",
            "timezone": "Asia/Kolkata",
            "active": "y",
        },
        follow_redirects=True,
    )
    assert b"Geofence updated" in response.data
    response = client.post(f"/admin/geofences/{gid}/delete", data={}, follow_redirects=True)
    assert b"Geofence deleted" in response.data
