from __future__ import annotations

import secrets
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth import role_required
from app.extensions import db
from app.forms import AttendanceForm, ComplaintForm, EmptyForm
from app.models import (
    AttendanceRecord,
    Complaint,
    ComplaintCategory,
    ComplaintStatus,
    Fee,
    FeePayment,
    Role,
    RoomAllocation,
    StudentProfile,
)
from app.services import BusinessError, mark_attendance

bp = Blueprint("student", __name__, url_prefix="/student")


def profile_or_404() -> StudentProfile:
    profile = db.session.scalar(
        select(StudentProfile)
        .where(StudentProfile.user_id == current_user.id)
        .options(
            selectinload(StudentProfile.course),
            selectinload(StudentProfile.academic_year),
            selectinload(StudentProfile.allocations).selectinload(RoomAllocation.room),
            selectinload(StudentProfile.complaints).selectinload(Complaint.category),
            selectinload(StudentProfile.fees)
            .selectinload(Fee.payments)
            .selectinload(FeePayment.payment_method),
            selectinload(StudentProfile.fees).selectinload(Fee.academic_year),
            selectinload(StudentProfile.fees).selectinload(Fee.fee_type),
            selectinload(StudentProfile.attendance_records),
        )
    )
    if profile is None:
        abort(404)
    return profile


def _complaint_choices(form: ComplaintForm) -> None:
    categories = db.session.scalars(
        select(ComplaintCategory)
        .where(ComplaintCategory.active.is_(True))
        .order_by(ComplaintCategory.name)
    ).all()
    form.category_id.choices = [(item.id, item.name) for item in categories]


@bp.get("/")
@role_required(Role.STUDENT)
def dashboard():
    profile = profile_or_404()
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    today_attendance = next(
        (item for item in profile.attendance_records if item.attendance_date == today), None
    )
    open_complaints = sum(
        1 for item in profile.complaints if item.status != ComplaintStatus.RESOLVED
    )
    balance = sum((fee.balance for fee in profile.fees), Decimal("0"))
    return render_template(
        "student/dashboard.html",
        profile=profile,
        attendance=today_attendance,
        open_complaints=open_complaints,
        balance=balance,
    )


@bp.route("/complaints", methods=["GET", "POST"])
@role_required(Role.STUDENT)
def complaints():
    profile = profile_or_404()
    form = ComplaintForm()
    _complaint_choices(form)
    if form.validate_on_submit():
        reference = f"CMP-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(3).upper()}"
        db.session.add(
            Complaint(
                reference=reference,
                student_id=profile.id,
                category_id=form.category_id.data,
                subject=form.subject.data.strip(),
                description=form.description.data.strip(),
            )
        )
        db.session.commit()
        flash("Complaint submitted.", "success")
        return redirect(url_for("student.complaints"))

    records = db.session.scalars(
        select(Complaint)
        .where(Complaint.student_id == profile.id)
        .options(selectinload(Complaint.category))
        .order_by(Complaint.created_at.desc())
    ).all()
    return render_template("student/complaints.html", form=form, complaints=records)


@bp.route("/complaints/<int:complaint_id>/edit", methods=["GET", "POST"])
@role_required(Role.STUDENT)
def edit_complaint(complaint_id: int):
    profile = profile_or_404()
    complaint = db.session.get(Complaint, complaint_id)
    if complaint is None or complaint.student_id != profile.id:
        abort(404)
    if complaint.status != ComplaintStatus.OPEN:
        flash("Only open complaints can be edited.", "error")
        return redirect(url_for("student.complaints"))

    form = ComplaintForm()
    _complaint_choices(form)
    if form.validate_on_submit():
        complaint.category_id = form.category_id.data
        complaint.subject = form.subject.data.strip()
        complaint.description = form.description.data.strip()
        db.session.commit()
        flash("Complaint updated.", "success")
        return redirect(url_for("student.complaints"))
    if not form.is_submitted():
        form.category_id.data = complaint.category_id
        form.subject.data = complaint.subject
        form.description.data = complaint.description
    return render_template("student/complaint_form.html", form=form, complaint=complaint)


@bp.post("/complaints/<int:complaint_id>/delete")
@role_required(Role.STUDENT)
def delete_complaint(complaint_id: int):
    profile = profile_or_404()
    complaint = db.session.get(Complaint, complaint_id)
    if complaint is None or complaint.student_id != profile.id:
        abort(404)
    if not EmptyForm().validate_on_submit():
        abort(400)
    if complaint.status != ComplaintStatus.OPEN:
        flash("Only open complaints can be deleted.", "error")
    else:
        db.session.delete(complaint)
        db.session.commit()
        flash("Complaint deleted.", "success")
    return redirect(url_for("student.complaints"))


@bp.get("/fees")
@role_required(Role.STUDENT)
def fees():
    profile = profile_or_404()
    records = db.session.scalars(
        select(Fee)
        .where(Fee.student_id == profile.id)
        .options(
            selectinload(Fee.payments).selectinload(FeePayment.payment_method),
            selectinload(Fee.academic_year),
            selectinload(Fee.fee_type),
        )
        .order_by(Fee.created_at.desc())
    ).all()
    return render_template("student/fees.html", fees=records)


@bp.route("/attendance", methods=["GET", "POST"])
@role_required(Role.STUDENT)
def attendance():
    profile = profile_or_404()
    form = AttendanceForm()
    if form.validate_on_submit():
        try:
            record = mark_attendance(
                profile, form.latitude.data, form.longitude.data, form.accuracy.data
            )
            flash(
                f"Attendance marked successfully. Distance: {record.distance_metres} metres.",
                "success",
            )
            return redirect(url_for("student.attendance"))
        except BusinessError as exc:
            flash(str(exc), "error")

    records = db.session.scalars(
        select(AttendanceRecord)
        .where(AttendanceRecord.student_id == profile.id)
        .order_by(AttendanceRecord.attendance_date.desc())
        .limit(60)
    ).all()
    return render_template("student/attendance.html", form=form, records=records)
