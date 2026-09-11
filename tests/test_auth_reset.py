from __future__ import annotations

import re

from app.extensions import db
from app.models import PasswordResetToken, User


def test_forgot_password_reset_is_single_use(app, client, seeded):
    response = client.post(
        "/forgot-password", data={"email": "student@example.com"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"If an active account exists" in response.data
    match = re.search(rb'href="http://localhost(/reset-password/[^\"]+)"', response.data)
    assert match is not None
    reset_path = match.group(1).decode()

    response = client.post(
        reset_path,
        data={"password": "Changed@123", "confirm_password": "Changed@123"},
        follow_redirects=True,
    )
    assert b"Password changed successfully" in response.data
    assert client.get(reset_path).status_code == 302

    response = client.post(
        "/login", data={"login": "student@example.com", "password": "Changed@123"}
    )
    assert response.status_code == 302

    with app.app_context():
        user = db.session.get(User, seeded["student_user_id"])
        assert user is not None and user.check_password("Changed@123")
        token = db.session.query(PasswordResetToken).filter_by(user_id=user.id).one()
        assert token.used_at is not None


def test_forgot_password_does_not_enumerate_accounts(client, seeded):
    known = client.post("/forgot-password", data={"email": "student@example.com"})
    unknown = client.post("/forgot-password", data={"email": "nobody@example.com"})
    message = b"If an active account exists"
    assert message in known.data and message in unknown.data
