from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, time
from decimal import Decimal

from flask_login import UserMixin
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role:
    ADMIN = "ADMIN"
    STUDENT = "STUDENT"


class ComplaintStatus:
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    ALL = (OPEN, IN_PROGRESS, RESOLVED)


class ResidentStatus:
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ReferenceMixin:
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Course(ReferenceMixin, Base):
    __tablename__ = "courses"
    students: Mapped[list[StudentProfile]] = relationship(back_populates="course")


class AcademicYear(ReferenceMixin, Base):
    __tablename__ = "academic_years"
    students: Mapped[list[StudentProfile]] = relationship(back_populates="academic_year")
    fees: Mapped[list[Fee]] = relationship(back_populates="academic_year")


class ComplaintCategory(ReferenceMixin, Base):
    __tablename__ = "complaint_categories"
    complaints: Mapped[list[Complaint]] = relationship(back_populates="category")


class FeeType(ReferenceMixin, Base):
    __tablename__ = "fee_types"
    fees: Mapped[list[Fee]] = relationship(back_populates="fee_type")


class PaymentMethod(ReferenceMixin, Base):
    __tablename__ = "payment_methods"
    payments: Mapped[list[FeePayment]] = relationship(back_populates="payment_method")


class Block(Base):
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    rooms: Mapped[list[Room]] = relationship(back_populates="block")


class User(UserMixin, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('ADMIN', 'STUDENT')", name="ck_user_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped[StudentProfile | None] = relationship(back_populates="user", uselist=False)
    reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.active

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("ix_password_reset_user_active", "user_id", "used_at", "expires_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="reset_tokens")

    @staticmethod
    def digest(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @property
    def is_valid(self) -> bool:
        now = utcnow()
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return self.used_at is None and expires > now


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint("resident_status IN ('ACTIVE', 'INACTIVE')", name="ck_resident_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), unique=True)
    student_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), index=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="RESTRICT"), index=True
    )
    academic_year_id: Mapped[int | None] = mapped_column(
        ForeignKey("academic_years.id", ondelete="RESTRICT"), index=True
    )
    guardian_name: Mapped[str | None] = mapped_column(String(160))
    guardian_phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(Text)
    resident_status: Mapped[str] = mapped_column(
        String(20), default=ResidentStatus.ACTIVE, nullable=False, index=True
    )
    joined_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(back_populates="profile")
    course: Mapped[Course | None] = relationship(back_populates="students")
    academic_year: Mapped[AcademicYear | None] = relationship(back_populates="students")
    allocations: Mapped[list[RoomAllocation]] = relationship(back_populates="student")
    complaints: Mapped[list[Complaint]] = relationship(back_populates="student")
    fees: Mapped[list[Fee]] = relationship(back_populates="student")
    attendance_records: Mapped[list[AttendanceRecord]] = relationship(back_populates="student")

    @property
    def current_allocation(self) -> RoomAllocation | None:
        return next((item for item in self.allocations if item.ended_on is None), None)


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("block_id", "number", name="uq_room_block_number"),
        CheckConstraint("capacity >= 1", name="ck_room_capacity_positive"),
        CheckConstraint("floor >= 0", name="ck_room_floor_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey("blocks.id", ondelete="RESTRICT"), index=True)
    number: Mapped[str] = mapped_column(String(20))
    floor: Mapped[int] = mapped_column(default=0)
    capacity: Mapped[int] = mapped_column(default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    block: Mapped[Block] = relationship(back_populates="rooms")
    allocations: Mapped[list[RoomAllocation]] = relationship(back_populates="room")

    @property
    def current_occupancy(self) -> int:
        return sum(1 for item in self.allocations if item.ended_on is None)

    @property
    def available_beds(self) -> int:
        return max(0, self.capacity - self.current_occupancy)


class RoomAllocation(Base):
    __tablename__ = "room_allocations"
    __table_args__ = (
        CheckConstraint("ended_on IS NULL OR ended_on >= started_on", name="ck_alloc_dates"),
        Index(
            "uq_room_alloc_current_student",
            "student_id",
            unique=True,
            sqlite_where=text("ended_on IS NULL"),
        ),
        Index(
            "uq_room_alloc_current_bed",
            "room_id",
            "bed_label",
            unique=True,
            sqlite_where=text("ended_on IS NULL AND bed_label IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="RESTRICT"), index=True
    )
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="RESTRICT"), index=True)
    bed_label: Mapped[str | None] = mapped_column(String(20))
    started_on: Mapped[date] = mapped_column(Date, default=date.today)
    ended_on: Mapped[date | None] = mapped_column(Date)
    allocated_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    student: Mapped[StudentProfile] = relationship(back_populates="allocations")
    room: Mapped[Room] = relationship(back_populates="allocations")


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')", name="ck_complaint_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="RESTRICT"), index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("complaint_categories.id", ondelete="RESTRICT"), index=True
    )
    subject: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default=ComplaintStatus.OPEN, index=True)
    admin_notes: Mapped[str | None] = mapped_column(Text)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    student: Mapped[StudentProfile] = relationship(back_populates="complaints")
    category: Mapped[ComplaintCategory] = relationship(back_populates="complaints")


class Fee(Base):
    __tablename__ = "fees"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "academic_year_id", "fee_type_id", name="uq_fee_period_type"
        ),
        CheckConstraint("amount_due >= 0", name="ck_fee_amount_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="RESTRICT"), index=True
    )
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="RESTRICT"), index=True
    )
    fee_type_id: Mapped[int] = mapped_column(
        ForeignKey("fee_types.id", ondelete="RESTRICT"), index=True
    )
    amount_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    due_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    student: Mapped[StudentProfile] = relationship(back_populates="fees")
    academic_year: Mapped[AcademicYear] = relationship(back_populates="fees")
    fee_type: Mapped[FeeType] = relationship(back_populates="fees")
    payments: Mapped[list[FeePayment]] = relationship(back_populates="fee")

    @property
    def amount_paid(self) -> Decimal:
        return sum((item.amount for item in self.payments), Decimal("0"))

    @property
    def balance(self) -> Decimal:
        return max(Decimal("0"), self.amount_due - self.amount_paid)

    @property
    def status(self) -> str:
        if self.balance == 0:
            return "PAID"
        if self.amount_paid > 0:
            return "PARTIAL"
        return "UNPAID"


class FeePayment(Base):
    __tablename__ = "fee_payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payment_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    fee_id: Mapped[int] = mapped_column(ForeignKey("fees.id", ondelete="RESTRICT"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid_on: Mapped[date] = mapped_column(Date, default=date.today)
    payment_method_id: Mapped[int] = mapped_column(
        ForeignKey("payment_methods.id", ondelete="RESTRICT"), index=True
    )
    reference: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    fee: Mapped[Fee] = relationship(back_populates="payments")
    payment_method: Mapped[PaymentMethod] = relationship(back_populates="payments")


class AttendanceGeofence(Base):
    __tablename__ = "attendance_geofences"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_geo_lat"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_geo_lng"),
        CheckConstraint("radius_metres > 0", name="ck_geo_radius"),
        CheckConstraint("max_accuracy_metres > 0", name="ck_geo_accuracy"),
        Index(
            "uq_one_active_geofence",
            "active",
            unique=True,
            sqlite_where=text("active = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    radius_metres: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    max_accuracy_metres: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    check_in_start: Mapped[time | None] = mapped_column(Time)
    check_in_end: Mapped[time | None] = mapped_column(Time)
    late_after: Mapped[time | None] = mapped_column(Time)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    attendance_records: Mapped[list[AttendanceRecord]] = relationship(back_populates="geofence")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("student_id", "attendance_date", name="uq_attendance_student_date"),
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_att_lat"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_att_lng"),
        CheckConstraint("accuracy_metres >= 0", name="ck_att_accuracy"),
        CheckConstraint("distance_metres >= 0", name="ck_att_distance"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="RESTRICT"), index=True
    )
    geofence_id: Mapped[int] = mapped_column(
        ForeignKey("attendance_geofences.id", ondelete="RESTRICT"), index=True
    )
    attendance_date: Mapped[date] = mapped_column(Date, index=True)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    accuracy_metres: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    distance_metres: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    student: Mapped[StudentProfile] = relationship(back_populates="attendance_records")
    geofence: Mapped[AttendanceGeofence] = relationship(back_populates="attendance_records")
