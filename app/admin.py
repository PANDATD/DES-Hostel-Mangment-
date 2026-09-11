from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.auth import role_required
from app.extensions import db
from app.forms import (
    AttendanceAdminForm,
    BlockForm,
    ComplaintAdminForm,
    ComplaintUpdateForm,
    EmptyForm,
    FeeCreateForm,
    FeeEditForm,
    GeofenceForm,
    MasterDataForm,
    PaymentForm,
    RoomAllocationForm,
    RoomForm,
    StudentCreateForm,
    StudentEditForm,
)
from app.models import (
    AcademicYear,
    AttendanceGeofence,
    AttendanceRecord,
    Block,
    Complaint,
    ComplaintCategory,
    ComplaintStatus,
    Course,
    Fee,
    FeePayment,
    FeeType,
    PaymentMethod,
    ResidentStatus,
    Role,
    Room,
    RoomAllocation,
    StudentProfile,
    User,
)
from app.services import BusinessError, allocate_room, end_allocation

bp = Blueprint("admin", __name__, url_prefix="/admin")

MASTER_MODELS = {
    "courses": (Course, "Courses"),
    "academic-years": (AcademicYear, "Academic years"),
    "complaint-categories": (ComplaintCategory, "Complaint categories"),
    "fee-types": (FeeType, "Fee types"),
    "payment-methods": (PaymentMethod, "Payment methods"),
}


def _active_choices(model, blank: bool = False) -> list[tuple[int, str]]:
    rows = db.session.scalars(
        select(model).where(model.active.is_(True)).order_by(model.name)
    ).all()
    choices = [(item.id, item.name) for item in rows]
    return ([(0, "— Not set —")] + choices) if blank else choices


def _student_choices(form) -> None:
    form.course_id.choices = _active_choices(Course, blank=True)
    form.academic_year_id.choices = _active_choices(AcademicYear, blank=True)


def _fee_choices(form) -> None:
    students = db.session.scalars(
        select(StudentProfile)
        .where(StudentProfile.resident_status == ResidentStatus.ACTIVE)
        .order_by(StudentProfile.student_code)
    ).all()
    form.student_id.choices = [(s.id, f"{s.student_code} — {s.full_name}") for s in students]
    form.academic_year_id.choices = _active_choices(AcademicYear)
    form.fee_type_id.choices = _active_choices(FeeType)


def _payment_choices(form: PaymentForm) -> None:
    form.payment_method_id.choices = _active_choices(PaymentMethod)


def _complaint_choices(form) -> None:
    form.category_id.choices = _active_choices(ComplaintCategory)


def _room_choices(form: RoomForm) -> None:
    blocks = db.session.scalars(select(Block).order_by(Block.name)).all()
    form.block_id.choices = [(b.id, b.name) for b in blocks]


@bp.get("/")
@role_required(Role.ADMIN)
def dashboard():
    students = (
        db.session.scalar(
            select(func.count(StudentProfile.id)).where(
                StudentProfile.resident_status == ResidentStatus.ACTIVE
            )
        )
        or 0
    )
    rooms = db.session.scalars(select(Room).options(selectinload(Room.allocations))).all()
    active_rooms = [room for room in rooms if room.active]
    total_beds = sum(room.capacity for room in active_rooms)
    occupied = sum(room.current_occupancy for room in active_rooms)
    open_complaints = (
        db.session.scalar(
            select(func.count(Complaint.id)).where(Complaint.status != ComplaintStatus.RESOLVED)
        )
        or 0
    )
    fees = db.session.scalars(select(Fee).options(selectinload(Fee.payments))).all()
    outstanding = sum((fee.balance for fee in fees), Decimal("0"))
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    attendance_today = (
        db.session.scalar(
            select(func.count(AttendanceRecord.id)).where(AttendanceRecord.attendance_date == today)
        )
        or 0
    )
    return render_template(
        "admin/dashboard.html",
        students=students,
        active_rooms=len(active_rooms),
        total_beds=total_beds,
        occupied=occupied,
        available=max(0, total_beds - occupied),
        open_complaints=open_complaints,
        outstanding=outstanding,
        attendance_today=attendance_today,
    )


@bp.route("/students", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def students():
    form = StudentCreateForm()
    _student_choices(form)
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip().lower(),
            email=form.email.data.strip().lower(),
            role=Role.STUDENT,
            active=True,
        )
        user.set_password(form.password.data)
        profile = StudentProfile(
            user=user,
            student_code=form.student_code.data.strip().upper(),
            full_name=form.full_name.data.strip(),
            phone=(form.phone.data or "").strip() or None,
            course_id=form.course_id.data or None,
            academic_year_id=form.academic_year_id.data or None,
            guardian_name=(form.guardian_name.data or "").strip() or None,
            guardian_phone=(form.guardian_phone.data or "").strip() or None,
            address=(form.address.data or "").strip() or None,
            joined_on=form.joined_on.data,
            resident_status=ResidentStatus.ACTIVE,
        )
        db.session.add(profile)
        try:
            db.session.commit()
            flash("Student created.", "success")
            return redirect(url_for("admin.students"))
        except IntegrityError:
            db.session.rollback()
            flash("Username, email, or student code already exists.", "error")

    records = db.session.scalars(
        select(StudentProfile)
        .options(
            selectinload(StudentProfile.user),
            selectinload(StudentProfile.course),
            selectinload(StudentProfile.academic_year),
            selectinload(StudentProfile.allocations).selectinload(RoomAllocation.room),
        )
        .order_by(StudentProfile.student_code)
    ).all()
    return render_template("admin/students.html", form=form, students=records)


@bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def edit_student(student_id: int):
    student = db.get_or_404(StudentProfile, student_id)
    form = StudentEditForm()
    _student_choices(form)
    if form.validate_on_submit():
        student.user.username = form.username.data.strip().lower()
        student.user.email = form.email.data.strip().lower()
        student.user.active = form.active.data
        if form.password.data:
            student.user.set_password(form.password.data)
        student.student_code = form.student_code.data.strip().upper()
        student.full_name = form.full_name.data.strip()
        student.phone = (form.phone.data or "").strip() or None
        student.course_id = form.course_id.data or None
        student.academic_year_id = form.academic_year_id.data or None
        student.guardian_name = (form.guardian_name.data or "").strip() or None
        student.guardian_phone = (form.guardian_phone.data or "").strip() or None
        student.address = (form.address.data or "").strip() or None
        student.resident_status = form.resident_status.data
        student.joined_on = form.joined_on.data
        if student.resident_status == ResidentStatus.INACTIVE and student.current_allocation:
            student.current_allocation.ended_on = date.today()
        try:
            db.session.commit()
            flash("Student updated.", "success")
            return redirect(url_for("admin.students"))
        except IntegrityError:
            db.session.rollback()
            flash("Username, email, or student code already exists.", "error")
    elif not form.is_submitted():
        form.username.data = student.user.username
        form.email.data = student.user.email
        form.student_code.data = student.student_code
        form.full_name.data = student.full_name
        form.phone.data = student.phone
        form.course_id.data = student.course_id or 0
        form.academic_year_id.data = student.academic_year_id or 0
        form.guardian_name.data = student.guardian_name
        form.guardian_phone.data = student.guardian_phone
        form.address.data = student.address
        form.resident_status.data = student.resident_status
        form.active.data = student.user.active
        form.joined_on.data = student.joined_on
    return render_template("admin/student_form.html", form=form, student=student)


@bp.post("/students/<int:student_id>/delete")
@role_required(Role.ADMIN)
def delete_student(student_id: int):
    student = db.get_or_404(StudentProfile, student_id)
    form = EmptyForm()
    if not form.validate_on_submit():
        abort(400)
    user = student.user
    fee_ids = list(db.session.scalars(select(Fee.id).where(Fee.student_id == student.id)))
    if fee_ids:
        db.session.execute(delete(FeePayment).where(FeePayment.fee_id.in_(fee_ids)))
        db.session.execute(delete(Fee).where(Fee.id.in_(fee_ids)))
    db.session.execute(delete(AttendanceRecord).where(AttendanceRecord.student_id == student.id))
    db.session.execute(delete(Complaint).where(Complaint.student_id == student.id))
    db.session.execute(delete(RoomAllocation).where(RoomAllocation.student_id == student.id))
    db.session.delete(student)
    db.session.flush()
    db.session.delete(user)
    db.session.commit()
    flash("Student and owned records deleted.", "success")
    return redirect(url_for("admin.students"))


@bp.route("/blocks", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def blocks():
    form = BlockForm()
    if form.validate_on_submit():
        db.session.add(
            Block(
                code=form.code.data.strip().upper(),
                name=form.name.data.strip(),
                active=form.active.data,
            )
        )
        try:
            db.session.commit()
            flash("Block created.", "success")
            return redirect(url_for("admin.blocks"))
        except IntegrityError:
            db.session.rollback()
            flash("Block code already exists.", "error")
    records = db.session.scalars(
        select(Block).options(selectinload(Block.rooms)).order_by(Block.name)
    ).all()
    return render_template("admin/blocks.html", form=form, blocks=records)


@bp.route("/blocks/<int:block_id>/edit", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def edit_block(block_id: int):
    block = db.get_or_404(Block, block_id)
    form = BlockForm(obj=block)
    if form.validate_on_submit():
        block.code = form.code.data.strip().upper()
        block.name = form.name.data.strip()
        block.active = form.active.data
        try:
            db.session.commit()
            flash("Block updated.", "success")
            return redirect(url_for("admin.blocks"))
        except IntegrityError:
            db.session.rollback()
            flash("Block code already exists.", "error")
    return render_template("admin/block_form.html", form=form, block=block)


@bp.post("/blocks/<int:block_id>/delete")
@role_required(Role.ADMIN)
def delete_block(block_id: int):
    block = db.get_or_404(Block, block_id)
    if not EmptyForm().validate_on_submit():
        abort(400)
    if block.rooms:
        flash("Delete or move all rooms before deleting this block.", "error")
    else:
        db.session.delete(block)
        db.session.commit()
        flash("Block deleted.", "success")
    return redirect(url_for("admin.blocks"))


@bp.route("/rooms", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def rooms():
    form = RoomAllocationForm()
    students = db.session.scalars(
        select(StudentProfile)
        .where(StudentProfile.resident_status == ResidentStatus.ACTIVE)
        .order_by(StudentProfile.student_code)
    ).all()
    room_records = db.session.scalars(
        select(Room)
        .options(selectinload(Room.block), selectinload(Room.allocations))
        .order_by(Room.floor, Room.number)
    ).all()
    form.student_id.choices = [(s.id, f"{s.student_code} — {s.full_name}") for s in students]
    form.room_id.choices = [
        (r.id, f"{r.block.name} / {r.number} — {r.available_beds} bed(s) free")
        for r in room_records
        if r.active
    ]
    if form.validate_on_submit():
        student = db.session.get(StudentProfile, form.student_id.data)
        room = db.session.get(Room, form.room_id.data)
        if not student or not room:
            flash("Student or room not found.", "error")
        else:
            try:
                allocate_room(student, room, form.bed_label.data, current_user)
                flash("Room allocation saved.", "success")
                return redirect(url_for("admin.rooms"))
            except BusinessError as exc:
                flash(str(exc), "error")
    allocations = db.session.scalars(
        select(RoomAllocation)
        .options(
            selectinload(RoomAllocation.student),
            selectinload(RoomAllocation.room).selectinload(Room.block),
        )
        .order_by(RoomAllocation.created_at.desc())
        .limit(300)
    ).all()
    return render_template(
        "admin/rooms.html", form=form, rooms=room_records, allocations=allocations
    )


@bp.route("/rooms/create", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def create_room():
    form = RoomForm()
    _room_choices(form)
    if form.validate_on_submit():
        room = Room(
            block_id=form.block_id.data,
            number=form.number.data.strip(),
            floor=form.floor.data,
            capacity=form.capacity.data,
            active=form.active.data,
        )
        db.session.add(room)
        try:
            db.session.commit()
            flash("Room created.", "success")
            return redirect(url_for("admin.rooms"))
        except IntegrityError:
            db.session.rollback()
            flash("That room number already exists in the selected block.", "error")
    return render_template("admin/room_form.html", form=form, room=None)


@bp.route("/rooms/<int:room_id>/edit", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def edit_room(room_id: int):
    room = db.get_or_404(Room, room_id)
    form = RoomForm(obj=room)
    _room_choices(form)
    if form.validate_on_submit():
        if form.capacity.data < room.current_occupancy:
            flash("Capacity cannot be lower than current occupancy.", "error")
        else:
            room.block_id = form.block_id.data
            room.number = form.number.data.strip()
            room.floor = form.floor.data
            room.capacity = form.capacity.data
            room.active = form.active.data
            try:
                db.session.commit()
                flash("Room updated.", "success")
                return redirect(url_for("admin.rooms"))
            except IntegrityError:
                db.session.rollback()
                flash("That room number already exists in the selected block.", "error")
    return render_template("admin/room_form.html", form=form, room=room)


@bp.post("/rooms/<int:room_id>/delete")
@role_required(Role.ADMIN)
def delete_room(room_id: int):
    room = db.get_or_404(Room, room_id)
    if not EmptyForm().validate_on_submit():
        abort(400)
    if room.allocations:
        flash(
            "Room allocation history exists; delete that history before deleting the room.", "error"
        )
    else:
        db.session.delete(room)
        db.session.commit()
        flash("Room deleted.", "success")
    return redirect(url_for("admin.rooms"))


@bp.post("/allocations/<int:allocation_id>/end")
@role_required(Role.ADMIN)
def end_room_allocation(allocation_id: int):
    allocation = db.get_or_404(RoomAllocation, allocation_id)
    if not EmptyForm().validate_on_submit():
        abort(400)
    try:
        end_allocation(allocation)
        flash("Room allocation ended.", "success")
    except BusinessError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin.rooms"))


@bp.post("/allocations/<int:allocation_id>/delete")
@role_required(Role.ADMIN)
def delete_room_allocation(allocation_id: int):
    allocation = db.get_or_404(RoomAllocation, allocation_id)
    if not EmptyForm().validate_on_submit():
        abort(400)
    if allocation.ended_on is None:
        flash("End the active allocation before deleting its history.", "error")
    else:
        db.session.delete(allocation)
        db.session.commit()
        flash("Allocation history deleted.", "success")
    return redirect(url_for("admin.rooms"))


@bp.get("/complaints")
@role_required(Role.ADMIN)
def complaints():
    records = db.session.scalars(
        select(Complaint)
        .options(selectinload(Complaint.student), selectinload(Complaint.category))
        .order_by(Complaint.created_at.desc())
    ).all()
    return render_template("admin/complaints.html", complaints=records, form=ComplaintUpdateForm())


@bp.post("/complaints/<int:complaint_id>")
@role_required(Role.ADMIN)
def update_complaint(complaint_id: int):
    complaint = db.get_or_404(Complaint, complaint_id)
    form = ComplaintUpdateForm()
    if form.validate_on_submit():
        complaint.status = form.status.data
        complaint.admin_notes = (form.admin_notes.data or "").strip() or None
        complaint.updated_by_user_id = current_user.id
        complaint.resolved_at = (
            datetime.now(UTC) if complaint.status == ComplaintStatus.RESOLVED else None
        )
        db.session.commit()
        flash("Complaint updated.", "success")
    else:
        flash("Invalid complaint update.", "error")
    return redirect(url_for("admin.complaints"))


@bp.route("/complaints/<int:complaint_id>/edit", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def edit_complaint(complaint_id: int):
    complaint = db.get_or_404(Complaint, complaint_id)
    form = ComplaintAdminForm()
    _complaint_choices(form)
    if form.validate_on_submit():
        complaint.category_id = form.category_id.data
        complaint.subject = form.subject.data.strip()
        complaint.description = form.description.data.strip()
        complaint.status = form.status.data
        complaint.admin_notes = (form.admin_notes.data or "").strip() or None
        complaint.updated_by_user_id = current_user.id
        complaint.resolved_at = (
            datetime.now(UTC) if complaint.status == ComplaintStatus.RESOLVED else None
        )
        db.session.commit()
        flash("Complaint updated.", "success")
        return redirect(url_for("admin.complaints"))
    elif not form.is_submitted():
        form.category_id.data = complaint.category_id
        form.subject.data = complaint.subject
        form.description.data = complaint.description
        form.status.data = complaint.status
        form.admin_notes.data = complaint.admin_notes
    return render_template("admin/complaint_form.html", form=form, complaint=complaint)


@bp.post("/complaints/<int:complaint_id>/delete")
@role_required(Role.ADMIN)
def delete_complaint(complaint_id: int):
    complaint = db.get_or_404(Complaint, complaint_id)
    if not EmptyForm().validate_on_submit():
        abort(400)
    db.session.delete(complaint)
    db.session.commit()
    flash("Complaint deleted.", "success")
    return redirect(url_for("admin.complaints"))


@bp.route("/fees", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def fees():
    create_form = FeeCreateForm()
    _fee_choices(create_form)
    payment_form = PaymentForm()
    _payment_choices(payment_form)
    if not payment_form.paid_on.data:
        payment_form.paid_on.data = date.today()
    if create_form.validate_on_submit():
        fee = Fee(
            student_id=create_form.student_id.data,
            academic_year_id=create_form.academic_year_id.data,
            fee_type_id=create_form.fee_type_id.data,
            amount_due=create_form.amount_due.data,
            due_date=create_form.due_date.data,
            notes=(create_form.notes.data or "").strip() or None,
        )
        db.session.add(fee)
        try:
            db.session.commit()
            flash("Fee record created.", "success")
            return redirect(url_for("admin.fees"))
        except IntegrityError:
            db.session.rollback()
            flash("This fee already exists for the student/year/type.", "error")

    records = db.session.scalars(
        select(Fee)
        .options(
            selectinload(Fee.student),
            selectinload(Fee.payments).selectinload(FeePayment.payment_method),
            selectinload(Fee.academic_year),
            selectinload(Fee.fee_type),
        )
        .order_by(Fee.created_at.desc())
    ).all()
    return render_template(
        "admin/fees.html", fees=records, create_form=create_form, payment_form=payment_form
    )


@bp.route("/fees/<int:fee_id>/edit", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def edit_fee(fee_id: int):
    fee = db.get_or_404(Fee, fee_id)
    form = FeeEditForm()
    _fee_choices(form)
    if form.validate_on_submit():
        if form.amount_due.data < fee.amount_paid:
            flash("Amount due cannot be lower than payments already recorded.", "error")
        else:
            fee.student_id = form.student_id.data
            fee.academic_year_id = form.academic_year_id.data
            fee.fee_type_id = form.fee_type_id.data
            fee.amount_due = form.amount_due.data
            fee.due_date = form.due_date.data
            fee.notes = (form.notes.data or "").strip() or None
            try:
                db.session.commit()
                flash("Fee updated.", "success")
                return redirect(url_for("admin.fees"))
            except IntegrityError:
                db.session.rollback()
                flash("A fee for that student/year/type already exists.", "error")
    elif not form.is_submitted():
        form.student_id.data = fee.student_id
        form.academic_year_id.data = fee.academic_year_id
        form.fee_type_id.data = fee.fee_type_id
        form.amount_due.data = fee.amount_due
        form.due_date.data = fee.due_date
        form.notes.data = fee.notes
    return render_template("admin/fee_form.html", form=form, fee=fee)


@bp.post("/fees/<int:fee_id>/delete")
@role_required(Role.ADMIN)
def delete_fee(fee_id: int):
    fee = db.get_or_404(Fee, fee_id)
    if not EmptyForm().validate_on_submit():
        abort(400)
    for payment in list(fee.payments):
        db.session.delete(payment)
    db.session.delete(fee)
    db.session.commit()
    flash("Fee and its payment records deleted.", "success")
    return redirect(url_for("admin.fees"))


@bp.post("/fees/<int:fee_id>/payment")
@role_required(Role.ADMIN)
def add_payment(fee_id: int):
    fee = db.get_or_404(Fee, fee_id)
    form = PaymentForm()
    _payment_choices(form)
    if form.validate_on_submit():
        if form.amount.data > fee.balance:
            flash("Payment cannot exceed outstanding balance.", "error")
        else:
            db.session.add(
                FeePayment(
                    fee_id=fee.id,
                    amount=form.amount.data,
                    paid_on=form.paid_on.data,
                    payment_method_id=form.payment_method_id.data,
                    reference=(form.reference.data or "").strip() or None,
                    notes=(form.notes.data or "").strip() or None,
                    recorded_by_user_id=current_user.id,
                )
            )
            db.session.commit()
            flash("Payment recorded.", "success")
    else:
        flash("Invalid payment.", "error")
    return redirect(url_for("admin.fees"))


@bp.route("/payments/<int:payment_id>/edit", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def edit_payment(payment_id: int):
    payment = db.get_or_404(FeePayment, payment_id)
    form = PaymentForm()
    _payment_choices(form)
    if form.validate_on_submit():
        max_allowed = payment.fee.balance + payment.amount
        if form.amount.data > max_allowed:
            flash("Payment cannot exceed the fee total.", "error")
        else:
            payment.amount = form.amount.data
            payment.paid_on = form.paid_on.data
            payment.payment_method_id = form.payment_method_id.data
            payment.reference = (form.reference.data or "").strip() or None
            payment.notes = (form.notes.data or "").strip() or None
            db.session.commit()
            flash("Payment updated.", "success")
            return redirect(url_for("admin.fees"))
    elif not form.is_submitted():
        form.amount.data = payment.amount
        form.paid_on.data = payment.paid_on
        form.payment_method_id.data = payment.payment_method_id
        form.reference.data = payment.reference
        form.notes.data = payment.notes
    return render_template("admin/payment_form.html", form=form, payment=payment)


@bp.post("/payments/<int:payment_id>/delete")
@role_required(Role.ADMIN)
def delete_payment(payment_id: int):
    payment = db.get_or_404(FeePayment, payment_id)
    if not EmptyForm().validate_on_submit():
        abort(400)
    db.session.delete(payment)
    db.session.commit()
    flash("Payment deleted.", "success")
    return redirect(url_for("admin.fees"))


@bp.get("/attendance")
@role_required(Role.ADMIN)
def attendance():
    records = db.session.scalars(
        select(AttendanceRecord)
        .options(selectinload(AttendanceRecord.student), selectinload(AttendanceRecord.geofence))
        .order_by(AttendanceRecord.checked_in_at.desc())
        .limit(500)
    ).all()
    geofences = db.session.scalars(
        select(AttendanceGeofence).order_by(AttendanceGeofence.name)
    ).all()
    return render_template("admin/attendance.html", records=records, geofences=geofences)


@bp.route("/attendance/<int:record_id>/edit", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def edit_attendance(record_id: int):
    record = db.get_or_404(AttendanceRecord, record_id)
    form = AttendanceAdminForm(obj=record)
    if form.validate_on_submit():
        record.attendance_date = form.attendance_date.data
        record.is_late = form.is_late.data
        try:
            db.session.commit()
            flash("Attendance record updated.", "success")
            return redirect(url_for("admin.attendance"))
        except IntegrityError:
            db.session.rollback()
            flash("That student already has attendance for the selected date.", "error")
    return render_template("admin/attendance_form.html", form=form, record=record)


@bp.post("/attendance/<int:record_id>/delete")
@role_required(Role.ADMIN)
def delete_attendance(record_id: int):
    record = db.get_or_404(AttendanceRecord, record_id)
    if not EmptyForm().validate_on_submit():
        abort(400)
    db.session.delete(record)
    db.session.commit()
    flash("Attendance record deleted.", "success")
    return redirect(url_for("admin.attendance"))


@bp.route("/geofences/create", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def create_geofence():
    form = GeofenceForm()
    if form.validate_on_submit():
        if form.active.data:
            for item in db.session.scalars(
                select(AttendanceGeofence).where(AttendanceGeofence.active.is_(True))
            ):
                item.active = False
            db.session.flush()
        item = AttendanceGeofence(
            name=form.name.data.strip(),
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            radius_metres=form.radius_metres.data,
            max_accuracy_metres=form.max_accuracy_metres.data,
            check_in_start=form.check_in_start.data,
            check_in_end=form.check_in_end.data,
            late_after=form.late_after.data,
            timezone=form.timezone.data.strip(),
            active=form.active.data,
        )
        db.session.add(item)
        db.session.commit()
        flash("Geofence created.", "success")
        return redirect(url_for("admin.attendance"))
    if not form.is_submitted():
        form.timezone.data = "Asia/Kolkata"
    return render_template("admin/geofence_form.html", form=form, geofence=None)


@bp.route("/geofences/<int:geofence_id>/edit", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def edit_geofence(geofence_id: int):
    geofence = db.get_or_404(AttendanceGeofence, geofence_id)
    form = GeofenceForm(obj=geofence)
    if form.validate_on_submit():
        if form.active.data:
            for item in db.session.scalars(
                select(AttendanceGeofence).where(
                    AttendanceGeofence.id != geofence.id, AttendanceGeofence.active.is_(True)
                )
            ):
                item.active = False
            db.session.flush()
        geofence.name = form.name.data.strip()
        geofence.latitude = form.latitude.data
        geofence.longitude = form.longitude.data
        geofence.radius_metres = form.radius_metres.data
        geofence.max_accuracy_metres = form.max_accuracy_metres.data
        geofence.check_in_start = form.check_in_start.data
        geofence.check_in_end = form.check_in_end.data
        geofence.late_after = form.late_after.data
        geofence.timezone = form.timezone.data.strip()
        geofence.active = form.active.data
        db.session.commit()
        flash("Geofence updated.", "success")
        return redirect(url_for("admin.attendance"))
    return render_template("admin/geofence_form.html", form=form, geofence=geofence)


@bp.post("/geofences/<int:geofence_id>/delete")
@role_required(Role.ADMIN)
def delete_geofence(geofence_id: int):
    geofence = db.get_or_404(AttendanceGeofence, geofence_id)
    if not EmptyForm().validate_on_submit():
        abort(400)
    if geofence.attendance_records:
        flash("This geofence has attendance history and cannot be deleted.", "error")
    else:
        db.session.delete(geofence)
        db.session.commit()
        flash("Geofence deleted.", "success")
    return redirect(url_for("admin.attendance"))


@bp.get("/master-data")
@role_required(Role.ADMIN)
def master_data():
    data = {
        kind: (label, db.session.scalars(select(model).order_by(model.name)).all())
        for kind, (model, label) in MASTER_MODELS.items()
    }
    return render_template("admin/master_data.html", data=data, form=MasterDataForm())


@bp.post("/master-data/<kind>")
@role_required(Role.ADMIN)
def create_master_data(kind: str):
    model_info = MASTER_MODELS.get(kind)
    if model_info is None:
        abort(404)
    model, label = model_info
    form = MasterDataForm()
    if form.validate_on_submit():
        db.session.add(
            model(
                code=form.code.data.strip().upper(),
                name=form.name.data.strip(),
                active=form.active.data,
            )
        )
        try:
            db.session.commit()
            flash(f"{label[:-1] if label.endswith('s') else label} created.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Code or name already exists.", "error")
    return redirect(url_for("admin.master_data"))


@bp.route("/master-data/<kind>/<int:item_id>/edit", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def edit_master_data(kind: str, item_id: int):
    model_info = MASTER_MODELS.get(kind)
    if model_info is None:
        abort(404)
    model, label = model_info
    item = db.get_or_404(model, item_id)
    form = MasterDataForm(obj=item)
    if form.validate_on_submit():
        item.code = form.code.data.strip().upper()
        item.name = form.name.data.strip()
        item.active = form.active.data
        try:
            db.session.commit()
            flash(f"{label} updated.", "success")
            return redirect(url_for("admin.master_data"))
        except IntegrityError:
            db.session.rollback()
            flash("Code or name already exists.", "error")
    return render_template("admin/master_form.html", form=form, label=label, item=item)


@bp.post("/master-data/<kind>/<int:item_id>/delete")
@role_required(Role.ADMIN)
def delete_master_data(kind: str, item_id: int):
    model_info = MASTER_MODELS.get(kind)
    if model_info is None:
        abort(404)
    model, _label = model_info
    item = db.get_or_404(model, item_id)
    if not EmptyForm().validate_on_submit():
        abort(400)
    db.session.delete(item)
    try:
        db.session.commit()
        flash("Master-data record deleted.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(
            "This value is still referenced and cannot be deleted. Deactivate it instead.", "error"
        )
    return redirect(url_for("admin.master_data"))
