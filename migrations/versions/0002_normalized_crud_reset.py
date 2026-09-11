"""Normalize reference data and add password reset tokens.

Revision ID: 0002_normalized_crud_reset
Revises: 0001_v1_schema
Create Date: 2026-09-07
"""
# ruff: noqa: E501

from __future__ import annotations

import re
from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op

revision = "0002_normalized_crud_reset"
down_revision = "0001_v1_schema"
branch_labels = None
depends_on = None


REF_TABLES = (
    "courses",
    "academic_years",
    "complaint_categories",
    "fee_types",
    "payment_methods",
)


def _create_reference_table(name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(f"ix_{name}_code", name, ["code"], unique=True)
    op.create_index(f"ix_{name}_active", name, ["active"])


def _slug(value: str, prefix: str, used: set[str]) -> str:
    base = re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-") or prefix
    base = base[:52]
    code = base
    number = 2
    while code in used:
        suffix = f"-{number}"
        code = f"{base[: 60 - len(suffix)]}{suffix}"
        number += 1
    used.add(code)
    return code


def _seed_from_values(table_name: str, values: Iterable[str], prefix: str) -> None:
    bind = op.get_bind()
    table = sa.table(
        table_name,
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("active", sa.Boolean()),
    )
    used: set[str] = set()
    rows = []
    for raw in values:
        value = (raw or "").strip()
        if not value:
            continue
        rows.append({"code": _slug(value, prefix, used), "name": value, "active": True})
    if rows:
        bind.execute(table.insert(), rows)


def _distinct(column_sql: str) -> list[str]:
    bind = op.get_bind()
    return [row[0] for row in bind.execute(sa.text(column_sql)).fetchall() if row[0]]


def upgrade() -> None:
    for name in REF_TABLES:
        _create_reference_table(name)

    _seed_from_values(
        "courses",
        _distinct(
            "SELECT DISTINCT course FROM student_profiles WHERE course IS NOT NULL AND trim(course) <> '' ORDER BY course"
        ),
        "COURSE",
    )
    _seed_from_values(
        "academic_years",
        _distinct(
            "SELECT academic_year FROM student_profiles WHERE academic_year IS NOT NULL AND trim(academic_year) <> '' "
            "UNION SELECT academic_year FROM fees WHERE academic_year IS NOT NULL AND trim(academic_year) <> '' ORDER BY 1"
        ),
        "YEAR",
    )
    _seed_from_values(
        "complaint_categories",
        _distinct(
            "SELECT DISTINCT category FROM complaints WHERE trim(category) <> '' ORDER BY category"
        ),
        "CATEGORY",
    )
    _seed_from_values(
        "fee_types",
        _distinct(
            "SELECT DISTINCT fee_type FROM fees WHERE trim(fee_type) <> '' ORDER BY fee_type"
        ),
        "FEE",
    )
    _seed_from_values(
        "payment_methods",
        _distinct(
            "SELECT DISTINCT payment_method FROM fee_payments WHERE trim(payment_method) <> '' ORDER BY payment_method"
        ),
        "PAYMENT",
    )

    # Ensure standard choices exist even if the old database has no rows yet.
    bind = op.get_bind()
    defaults = {
        "complaint_categories": [
            ("ELECTRICAL", "Electrical"),
            ("PLUMBING", "Plumbing"),
            ("CLEANING", "Cleaning"),
            ("FURNITURE", "Furniture"),
            ("MESS", "Mess / Food"),
            ("SECURITY", "Security"),
            ("OTHER", "Other"),
        ],
        "fee_types": [("HOSTEL", "Hostel Fee")],
        "payment_methods": [("CASH", "Cash"), ("UPI", "UPI"), ("BANK", "Bank"), ("OTHER", "Other")],
    }
    for table_name, items in defaults.items():
        for code, name in items:
            exists = bind.execute(
                sa.text(f"SELECT 1 FROM {table_name} WHERE name=:name OR code=:code LIMIT 1"),
                {"name": name, "code": code},
            ).first()
            if not exists:
                bind.execute(
                    sa.text(
                        f"INSERT INTO {table_name}(code,name,active,created_at,updated_at) VALUES (:code,:name,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
                    ),
                    {"code": code, "name": name},
                )

    with op.batch_alter_table("student_profiles") as batch:
        batch.add_column(sa.Column("course_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("academic_year_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_student_course", "courses", ["course_id"], ["id"], ondelete="RESTRICT"
        )
        batch.create_foreign_key(
            "fk_student_academic_year",
            "academic_years",
            ["academic_year_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    bind.execute(
        sa.text(
            "UPDATE student_profiles SET course_id=(SELECT id FROM courses WHERE courses.name=student_profiles.course) WHERE course IS NOT NULL AND trim(course)<>''"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE student_profiles SET academic_year_id=(SELECT id FROM academic_years WHERE academic_years.name=student_profiles.academic_year) WHERE academic_year IS NOT NULL AND trim(academic_year)<>''"
        )
    )
    with op.batch_alter_table("student_profiles") as batch:
        batch.drop_column("course")
        batch.drop_column("academic_year")
    op.create_index("ix_student_profiles_course_id", "student_profiles", ["course_id"])
    op.create_index(
        "ix_student_profiles_academic_year_id", "student_profiles", ["academic_year_id"]
    )

    with op.batch_alter_table("complaints") as batch:
        batch.add_column(sa.Column("category_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_complaint_category",
            "complaint_categories",
            ["category_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    bind.execute(
        sa.text(
            "UPDATE complaints SET category_id=(SELECT id FROM complaint_categories WHERE complaint_categories.name=complaints.category)"
        )
    )
    with op.batch_alter_table("complaints") as batch:
        batch.alter_column("category_id", existing_type=sa.Integer(), nullable=False)
        batch.drop_column("category")
    op.create_index("ix_complaints_student_id", "complaints", ["student_id"])
    op.create_index("ix_complaints_category_id", "complaints", ["category_id"])

    with op.batch_alter_table("fees") as batch:
        batch.drop_constraint("uq_fee_period_type", type_="unique")
        batch.add_column(sa.Column("academic_year_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("fee_type_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_fee_academic_year",
            "academic_years",
            ["academic_year_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_fee_type", "fee_types", ["fee_type_id"], ["id"], ondelete="RESTRICT"
        )
    bind.execute(
        sa.text(
            "UPDATE fees SET academic_year_id=(SELECT id FROM academic_years WHERE academic_years.name=fees.academic_year)"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE fees SET fee_type_id=(SELECT id FROM fee_types WHERE fee_types.name=fees.fee_type)"
        )
    )
    with op.batch_alter_table("fees") as batch:
        batch.alter_column("academic_year_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("fee_type_id", existing_type=sa.Integer(), nullable=False)
        batch.drop_column("academic_year")
        batch.drop_column("fee_type")
        batch.create_unique_constraint(
            "uq_fee_period_type", ["student_id", "academic_year_id", "fee_type_id"]
        )
    op.create_index("ix_fees_student_id", "fees", ["student_id"])
    op.create_index("ix_fees_academic_year_id", "fees", ["academic_year_id"])
    op.create_index("ix_fees_fee_type_id", "fees", ["fee_type_id"])

    with op.batch_alter_table("fee_payments") as batch:
        batch.drop_constraint("ck_payment_method", type_="check")
        batch.add_column(sa.Column("payment_method_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_payment_method",
            "payment_methods",
            ["payment_method_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    bind.execute(
        sa.text(
            "UPDATE fee_payments SET payment_method_id=(SELECT id FROM payment_methods WHERE payment_methods.name=fee_payments.payment_method OR payment_methods.code=fee_payments.payment_method LIMIT 1)"
        )
    )
    with op.batch_alter_table("fee_payments") as batch:
        batch.alter_column("payment_method_id", existing_type=sa.Integer(), nullable=False)
        batch.drop_column("payment_method")
    op.create_index("ix_fee_payments_fee_id", "fee_payments", ["fee_id"])
    op.create_index("ix_fee_payments_payment_method_id", "fee_payments", ["payment_method_id"])

    op.create_index("ix_rooms_block_id", "rooms", ["block_id"])
    op.create_index("ix_room_allocations_student_id", "room_allocations", ["student_id"])
    op.create_index("ix_room_allocations_room_id", "room_allocations", ["room_id"])
    op.create_index("ix_attendance_records_student_id", "attendance_records", ["student_id"])
    op.create_index("ix_attendance_records_geofence_id", "attendance_records", ["geofence_id"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index(
        "ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True
    )
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])
    op.create_index(
        "ix_password_reset_user_active",
        "password_reset_tokens",
        ["user_id", "used_at", "expires_at"],
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")

    with op.batch_alter_table("fee_payments") as batch:
        batch.add_column(sa.Column("payment_method", sa.String(20), nullable=True))
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE fee_payments SET payment_method=(SELECT code FROM payment_methods WHERE payment_methods.id=fee_payments.payment_method_id)"
        )
    )
    with op.batch_alter_table("fee_payments") as batch:
        batch.alter_column("payment_method", existing_type=sa.String(20), nullable=False)
        batch.drop_column("payment_method_id")
        batch.create_check_constraint(
            "ck_payment_method", "payment_method IN ('CASH', 'UPI', 'BANK', 'OTHER')"
        )

    with op.batch_alter_table("fees") as batch:
        batch.drop_constraint("uq_fee_period_type", type_="unique")
        batch.add_column(sa.Column("academic_year", sa.String(30), nullable=True))
        batch.add_column(sa.Column("fee_type", sa.String(40), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE fees SET academic_year=(SELECT name FROM academic_years WHERE academic_years.id=fees.academic_year_id), fee_type=(SELECT code FROM fee_types WHERE fee_types.id=fees.fee_type_id)"
        )
    )
    with op.batch_alter_table("fees") as batch:
        batch.alter_column("academic_year", existing_type=sa.String(30), nullable=False)
        batch.alter_column("fee_type", existing_type=sa.String(40), nullable=False)
        batch.drop_column("academic_year_id")
        batch.drop_column("fee_type_id")
        batch.create_unique_constraint(
            "uq_fee_period_type", ["student_id", "academic_year", "fee_type"]
        )

    with op.batch_alter_table("complaints") as batch:
        batch.add_column(sa.Column("category", sa.String(60), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE complaints SET category=(SELECT name FROM complaint_categories WHERE complaint_categories.id=complaints.category_id)"
        )
    )
    with op.batch_alter_table("complaints") as batch:
        batch.alter_column("category", existing_type=sa.String(60), nullable=False)
        batch.drop_column("category_id")

    with op.batch_alter_table("student_profiles") as batch:
        batch.add_column(sa.Column("course", sa.String(160), nullable=True))
        batch.add_column(sa.Column("academic_year", sa.String(30), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE student_profiles SET course=(SELECT name FROM courses WHERE courses.id=student_profiles.course_id), academic_year=(SELECT name FROM academic_years WHERE academic_years.id=student_profiles.academic_year_id)"
        )
    )
    with op.batch_alter_table("student_profiles") as batch:
        batch.drop_column("course_id")
        batch.drop_column("academic_year_id")

    for name in reversed(REF_TABLES):
        op.drop_table(name)
