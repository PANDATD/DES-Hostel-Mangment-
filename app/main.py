from __future__ import annotations

from flask import Blueprint, redirect, url_for
from flask_login import current_user

from app.models import Role

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role == Role.ADMIN:
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("student.dashboard"))
