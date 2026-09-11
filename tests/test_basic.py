from __future__ import annotations

from decimal import Decimal

from app.services import haversine_metres


def test_haversine_same_point_is_zero():
    assert haversine_metres(
        Decimal("18.5204"), Decimal("73.8567"), Decimal("18.5204"), Decimal("73.8567")
    ) == Decimal("0.0")


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign in" in response.data


def test_admin_login(client, seeded):
    response = client.post(
        "/login",
        data={"login": "admin@example.com", "password": "Admin@123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Admin Dashboard" in response.data
