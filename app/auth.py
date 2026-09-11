from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, or_, select

from app.extensions import db
from app.forms import ForgotPasswordForm, LoginForm, ResetPasswordForm
from app.models import User, utcnow
from app.services import (
    consume_password_reset_token,
    create_password_reset_token,
    deliver_password_reset_email,
    get_valid_password_reset_token,
)

bp = Blueprint("auth", __name__)
F = TypeVar("F", bound=Callable[..., Any])


def role_required(role: str) -> Callable[[F], F]:
    def decorator(view: F) -> F:
        @wraps(view)
        @login_required
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if current_user.role != role:
                flash("You do not have permission to access that page.", "error")
                return redirect(url_for("main.index"))
            return view(*args, **kwargs)

        return cast(F, wrapped)

    return decorator


@bp.route("/login", methods=["GET", "POST"])
def login() -> Any:
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        identity = form.login.data.strip().lower()
        user = db.session.scalar(
            select(User).where(
                or_(func.lower(User.username) == identity, func.lower(User.email) == identity)
            )
        )
        if user and user.active and user.check_password(form.password.data):
            user.last_login_at = utcnow()
            db.session.commit()
            login_user(user)
            return redirect(url_for("main.index"))
        flash("Invalid username/email or password.", "error")
    return render_template("auth/login.html", form=form)


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password() -> Any:
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = ForgotPasswordForm()
    reset_url: str | None = None
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.scalar(select(User).where(func.lower(User.email) == email))
        if user and user.active:
            raw_token = create_password_reset_token(
                user, int(current_app.config["PASSWORD_RESET_TTL_MINUTES"])
            )
            reset_url = url_for("auth.reset_password", token=raw_token, _external=True)
            sent = deliver_password_reset_email(user, reset_url)
            if sent:
                reset_url = None
            elif not current_app.config.get("PASSWORD_RESET_SHOW_LINK", False):
                reset_url = None

        flash(
            "If an active account exists for that email, "
            "password reset instructions are available.",
            "success",
        )
        # Never reveal whether the address exists. Development can show a generated URL only
        # when explicitly configured, which makes the standalone demo usable without SMTP.
        return render_template("auth/forgot_password.html", form=form, reset_url=reset_url)

    return render_template("auth/forgot_password.html", form=form, reset_url=None)


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str) -> Any:
    if current_user.is_authenticated:
        logout_user()

    reset_record = get_valid_password_reset_token(token)
    if reset_record is None:
        flash("That password reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        consume_password_reset_token(reset_record, form.password.data)
        flash("Password changed successfully. You can now sign in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form)


@bp.post("/logout")
@login_required
def logout() -> Any:
    logout_user()
    return redirect(url_for("auth.login"))
