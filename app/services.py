from __future__ import annotations

import math
import secrets
import smtplib
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    AttendanceGeofence,
    AttendanceRecord,
    PasswordResetToken,
    ResidentStatus,
    Room,
    RoomAllocation,
    StudentProfile,
    User,
    utcnow,
)


class BusinessError(ValueError):
    pass


def allocate_room(student: StudentProfile, room: Room, bed_label: str | None, admin: User) -> None:
    if student.resident_status != ResidentStatus.ACTIVE:
        raise BusinessError("Student is inactive.")
    if not room.active:
        raise BusinessError("Room is inactive.")

    normalized_bed = bed_label.strip() if bed_label else None
    current = student.current_allocation
    if current and current.room_id == room.id and current.bed_label == normalized_bed:
        return

    occupancy = (
        db.session.scalar(
            select(db.func.count(RoomAllocation.id)).where(
                RoomAllocation.room_id == room.id,
                RoomAllocation.ended_on.is_(None),
            )
        )
        or 0
    )
    if current and current.room_id == room.id:
        occupancy -= 1
    if occupancy >= room.capacity:
        raise BusinessError("Room is full.")

    if normalized_bed:
        existing_bed = db.session.scalar(
            select(RoomAllocation.id).where(
                RoomAllocation.room_id == room.id,
                RoomAllocation.bed_label == normalized_bed,
                RoomAllocation.ended_on.is_(None),
                RoomAllocation.student_id != student.id,
            )
        )
        if existing_bed:
            raise BusinessError("That bed is already occupied.")

    today = date.today()
    if current:
        current.ended_on = today

    db.session.add(
        RoomAllocation(
            student_id=student.id,
            room_id=room.id,
            bed_label=normalized_bed,
            started_on=today,
            allocated_by_user_id=admin.id,
        )
    )
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise BusinessError("Room allocation conflicts with an existing allocation.") from exc


def end_allocation(allocation: RoomAllocation) -> None:
    if allocation.ended_on is not None:
        raise BusinessError("Allocation has already ended.")
    allocation.ended_on = date.today()
    db.session.commit()


def create_password_reset_token(user: User, lifetime_minutes: int) -> str:
    now = utcnow()
    for token in user.reset_tokens:
        if token.used_at is None:
            token.used_at = now

    raw_token = secrets.token_urlsafe(32)
    db.session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=PasswordResetToken.digest(raw_token),
            expires_at=now + timedelta(minutes=lifetime_minutes),
        )
    )
    db.session.commit()
    return raw_token


def get_valid_password_reset_token(raw_token: str) -> PasswordResetToken | None:
    if not raw_token or len(raw_token) > 512:
        return None
    token = db.session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == PasswordResetToken.digest(raw_token)
        )
    )
    if token is None or not token.is_valid or not token.user.active:
        return None
    return token


def consume_password_reset_token(token: PasswordResetToken, new_password: str) -> None:
    token.user.set_password(new_password)
    now = utcnow()
    token.used_at = now
    # Invalidate any other outstanding reset links for this user.
    for item in token.user.reset_tokens:
        if item.id != token.id and item.used_at is None:
            item.used_at = now
    db.session.commit()


def deliver_password_reset_email(user: User, reset_url: str) -> bool:
    """Send a password reset email using stdlib SMTP.

    Returns False when SMTP is intentionally not configured/suppressed. The caller may
    expose the link only in development/testing when configured to do so.
    """
    if current_app.config.get("MAIL_SUPPRESS_SEND", False):
        return False

    host = str(current_app.config.get("MAIL_SERVER", "")).strip()
    if not host:
        current_app.logger.warning("MAIL_SERVER is not configured; reset email was not sent")
        return False

    port = int(current_app.config.get("MAIL_PORT", 587))
    username = str(current_app.config.get("MAIL_USERNAME", "")).strip()
    password = str(current_app.config.get("MAIL_PASSWORD", ""))
    use_tls = bool(current_app.config.get("MAIL_USE_TLS", True))
    sender = str(current_app.config.get("MAIL_DEFAULT_SENDER", "")).strip() or username
    if not sender:
        current_app.logger.warning(
            "MAIL_DEFAULT_SENDER is not configured; reset email was not sent"
        )
        return False

    message = EmailMessage()
    message["Subject"] = "Hostel Management password reset"
    message["From"] = sender
    message["To"] = user.email
    message.set_content(
        "A password reset was requested for your Hostel Management account.\n\n"
        f"Reset your password: {reset_url}\n\n"
        "If you did not request this, ignore this email. The link will expire automatically."
    )

    timeout = float(current_app.config.get("MAIL_TIMEOUT", 10))
    try:
        with smtplib.SMTP(host, port, timeout=timeout) as smtp:
            if use_tls:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        current_app.logger.exception("Could not send password reset email")
        return False


def haversine_metres(lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> Decimal:
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2 - lat1))
    delta_lambda = math.radians(float(lon2 - lon1))
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    distance = 2 * 6_371_000 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return Decimal(str(round(distance, 2)))


def _inside_time_window(now_time: time, start: time | None, end: time | None) -> bool:
    if start is None or end is None:
        return True
    if start <= end:
        return start <= now_time <= end
    return now_time >= start or now_time <= end


def mark_attendance(
    student: StudentProfile, latitude_raw: str, longitude_raw: str, accuracy_raw: str
) -> AttendanceRecord:
    if student.resident_status != ResidentStatus.ACTIVE:
        raise BusinessError("Inactive students cannot mark attendance.")

    try:
        latitude = Decimal(latitude_raw)
        longitude = Decimal(longitude_raw)
        accuracy = Decimal(accuracy_raw)
    except (InvalidOperation, TypeError) as exc:
        raise BusinessError("Invalid location data.") from exc

    if not Decimal("-90") <= latitude <= Decimal("90"):
        raise BusinessError("Invalid latitude.")
    if not Decimal("-180") <= longitude <= Decimal("180"):
        raise BusinessError("Invalid longitude.")
    if accuracy < 0:
        raise BusinessError("Invalid location accuracy.")

    geofence = db.session.scalar(
        select(AttendanceGeofence).where(AttendanceGeofence.active.is_(True))
    )
    if geofence is None:
        raise BusinessError("Attendance location is not configured.")
    if accuracy > geofence.max_accuracy_metres:
        raise BusinessError(
            f"Location accuracy is too low. Required ≤ {geofence.max_accuracy_metres} metres."
        )

    distance = haversine_metres(latitude, longitude, geofence.latitude, geofence.longitude)
    if distance > geofence.radius_metres:
        raise BusinessError(f"You are outside the hostel attendance area ({distance} m away).")

    now_utc = datetime.now(UTC)
    local_now = now_utc.astimezone(ZoneInfo(geofence.timezone))
    if not _inside_time_window(local_now.time(), geofence.check_in_start, geofence.check_in_end):
        raise BusinessError("Attendance is closed at this time.")

    attendance_day = local_now.date()
    is_late = geofence.late_after is not None and local_now.time() > geofence.late_after

    record = AttendanceRecord(
        student_id=student.id,
        geofence_id=geofence.id,
        attendance_date=attendance_day,
        checked_in_at=now_utc,
        latitude=latitude,
        longitude=longitude,
        accuracy_metres=accuracy,
        distance_metres=distance,
        is_late=is_late,
    )
    db.session.add(record)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise BusinessError("Attendance is already marked for today.") from exc
    return record
