"""V1 hostel schema.

Revision ID: 0001_v1_schema
Revises:
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_v1_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
        sa.CheckConstraint("role IN ('ADMIN', 'STUDENT')", name="ck_user_role"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_active", "users", ["active"])

    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("student_code", sa.String(40), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("course", sa.String(160), nullable=True),
        sa.Column("academic_year", sa.String(30), nullable=True),
        sa.Column("guardian_name", sa.String(160), nullable=True),
        sa.Column("guardian_phone", sa.String(20), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("resident_status", sa.String(20), nullable=False),
        sa.Column("joined_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("student_code"),
        sa.CheckConstraint("resident_status IN ('ACTIVE', 'INACTIVE')", name="ck_resident_status"),
    )
    op.create_index("ix_student_profiles_student_code", "student_profiles", ["student_code"])
    op.create_index("ix_student_profiles_full_name", "student_profiles", ["full_name"])
    op.create_index("ix_student_profiles_resident_status", "student_profiles", ["resident_status"])

    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(20), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["block_id"], ["blocks.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("block_id", "number", name="uq_room_block_number"),
        sa.CheckConstraint("capacity >= 1", name="ck_room_capacity_positive"),
        sa.CheckConstraint("floor >= 0", name="ck_room_floor_nonnegative"),
    )
    op.create_index("ix_rooms_active", "rooms", ["active"])

    op.create_table(
        "room_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("bed_label", sa.String(20), nullable=True),
        sa.Column("started_on", sa.Date(), nullable=False),
        sa.Column("ended_on", sa.Date(), nullable=True),
        sa.Column("allocated_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["allocated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("ended_on IS NULL OR ended_on >= started_on", name="ck_alloc_dates"),
    )
    op.create_index(
        "uq_room_alloc_current_student",
        "room_allocations",
        ["student_id"],
        unique=True,
        sqlite_where=sa.text("ended_on IS NULL"),
        postgresql_where=sa.text("ended_on IS NULL"),
    )
    op.create_index(
        "uq_room_alloc_current_bed",
        "room_allocations",
        ["room_id", "bed_label"],
        unique=True,
        sqlite_where=sa.text("ended_on IS NULL AND bed_label IS NOT NULL"),
        postgresql_where=sa.text("ended_on IS NULL AND bed_label IS NOT NULL"),
    )

    op.create_table(
        "complaints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reference", sa.String(32), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("subject", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("reference"),
        sa.CheckConstraint("status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')", name="ck_complaint_status"),
    )
    op.create_index("ix_complaints_reference", "complaints", ["reference"])
    op.create_index("ix_complaints_status", "complaints", ["status"])
    op.create_index("ix_complaints_created_at", "complaints", ["created_at"])

    op.create_table(
        "fees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("academic_year", sa.String(30), nullable=False),
        sa.Column("fee_type", sa.String(40), nullable=False),
        sa.Column("amount_due", sa.Numeric(12, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("student_id", "academic_year", "fee_type", name="uq_fee_period_type"),
        sa.CheckConstraint("amount_due >= 0", name="ck_fee_amount_nonnegative"),
    )

    op.create_table(
        "fee_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fee_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["fee_id"], ["fees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("amount > 0", name="ck_payment_positive"),
        sa.CheckConstraint("payment_method IN ('CASH', 'UPI', 'BANK', 'OTHER')", name="ck_payment_method"),
    )

    op.create_table(
        "attendance_geofences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("radius_metres", sa.Numeric(8, 2), nullable=False),
        sa.Column("max_accuracy_metres", sa.Numeric(8, 2), nullable=False),
        sa.Column("check_in_start", sa.Time(), nullable=True),
        sa.Column("check_in_end", sa.Time(), nullable=True),
        sa.Column("late_after", sa.Time(), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_geo_lat"),
        sa.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_geo_lng"),
        sa.CheckConstraint("radius_metres > 0", name="ck_geo_radius"),
        sa.CheckConstraint("max_accuracy_metres > 0", name="ck_geo_accuracy"),
    )
    op.create_index("ix_attendance_geofences_active", "attendance_geofences", ["active"])
    op.create_index(
        "uq_one_active_geofence",
        "attendance_geofences",
        ["active"],
        unique=True,
        sqlite_where=sa.text("active = 1"),
        postgresql_where=sa.text("active IS TRUE"),
    )

    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("geofence_id", sa.Integer(), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("accuracy_metres", sa.Numeric(8, 2), nullable=False),
        sa.Column("distance_metres", sa.Numeric(8, 2), nullable=False),
        sa.Column("is_late", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["geofence_id"], ["attendance_geofences.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("student_id", "attendance_date", name="uq_attendance_student_date"),
        sa.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_att_lat"),
        sa.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_att_lng"),
        sa.CheckConstraint("accuracy_metres >= 0", name="ck_att_accuracy"),
        sa.CheckConstraint("distance_metres >= 0", name="ck_att_distance"),
    )
    op.create_index("ix_attendance_records_attendance_date", "attendance_records", ["attendance_date"])


def downgrade() -> None:
    op.drop_table("attendance_records")
    op.drop_table("attendance_geofences")
    op.drop_table("fee_payments")
    op.drop_table("fees")
    op.drop_table("complaints")
    op.drop_table("room_allocations")
    op.drop_table("rooms")
    op.drop_table("student_profiles")
    op.drop_table("users")
    op.drop_table("blocks")
