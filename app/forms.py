from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    HiddenField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import Email, EqualTo, InputRequired, Length, NumberRange, Optional

from app.models import ComplaintStatus, ResidentStatus


class LoginForm(FlaskForm):
    login = StringField("Username or email", validators=[InputRequired(), Length(max=255)])
    password = PasswordField("Password", validators=[InputRequired(), Length(max=255)])
    submit = SubmitField("Sign in")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email(), Length(max=255)])
    submit = SubmitField("Send reset link")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New password", validators=[InputRequired(), Length(min=8, max=255)])
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[InputRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Reset password")


class StudentCreateForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[InputRequired(), Email(), Length(max=255)])
    password = PasswordField("Temporary password", validators=[InputRequired(), Length(min=8)])
    student_code = StringField("Student code", validators=[InputRequired(), Length(max=40)])
    full_name = StringField("Full name", validators=[InputRequired(), Length(max=160)])
    phone = StringField("Phone", validators=[Optional(), Length(max=20)])
    course_id = SelectField("Course", coerce=int, validators=[Optional()])
    academic_year_id = SelectField("Academic year", coerce=int, validators=[Optional()])
    guardian_name = StringField("Guardian name", validators=[Optional(), Length(max=160)])
    guardian_phone = StringField("Guardian phone", validators=[Optional(), Length(max=20)])
    address = TextAreaField("Address", validators=[Optional(), Length(max=2000)])
    joined_on = DateField("Joined on", validators=[Optional()])
    submit = SubmitField("Create student")


class StudentEditForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[InputRequired(), Email(), Length(max=255)])
    password = PasswordField("New password (optional)", validators=[Optional(), Length(min=8)])
    student_code = StringField("Student code", validators=[InputRequired(), Length(max=40)])
    full_name = StringField("Full name", validators=[InputRequired(), Length(max=160)])
    phone = StringField("Phone", validators=[Optional(), Length(max=20)])
    course_id = SelectField("Course", coerce=int, validators=[Optional()])
    academic_year_id = SelectField("Academic year", coerce=int, validators=[Optional()])
    guardian_name = StringField("Guardian name", validators=[Optional(), Length(max=160)])
    guardian_phone = StringField("Guardian phone", validators=[Optional(), Length(max=20)])
    address = TextAreaField("Address", validators=[Optional(), Length(max=2000)])
    resident_status = SelectField(
        "Resident status",
        choices=[(ResidentStatus.ACTIVE, "Active"), (ResidentStatus.INACTIVE, "Inactive")],
        validators=[InputRequired()],
    )
    active = BooleanField("Login enabled", default=True)
    joined_on = DateField("Joined on", validators=[Optional()])
    submit = SubmitField("Save student")


class BlockForm(FlaskForm):
    code = StringField("Code", validators=[InputRequired(), Length(max=40)])
    name = StringField("Name", validators=[InputRequired(), Length(max=100)])
    active = BooleanField("Active", default=True)
    submit = SubmitField("Save block")


class RoomForm(FlaskForm):
    block_id = SelectField("Block", coerce=int, validators=[InputRequired()])
    number = StringField("Room number", validators=[InputRequired(), Length(max=20)])
    floor = IntegerField("Floor", validators=[InputRequired(), NumberRange(min=0)])
    capacity = IntegerField("Capacity", validators=[InputRequired(), NumberRange(min=1, max=100)])
    active = BooleanField("Active", default=True)
    submit = SubmitField("Save room")


class RoomAllocationForm(FlaskForm):
    student_id = SelectField("Student", coerce=int, validators=[InputRequired()])
    room_id = SelectField("Room", coerce=int, validators=[InputRequired()])
    bed_label = StringField("Bed", validators=[Optional(), Length(max=20)])
    submit = SubmitField("Allocate room")


class ComplaintForm(FlaskForm):
    category_id = SelectField("Category", coerce=int, validators=[InputRequired()])
    subject = StringField("Subject", validators=[InputRequired(), Length(min=3, max=160)])
    description = TextAreaField(
        "Description", validators=[InputRequired(), Length(min=5, max=4000)]
    )
    submit = SubmitField("Submit complaint")


class ComplaintAdminForm(ComplaintForm):
    status = SelectField(
        "Status",
        choices=[
            (ComplaintStatus.OPEN, "Open"),
            (ComplaintStatus.IN_PROGRESS, "In progress"),
            (ComplaintStatus.RESOLVED, "Resolved"),
        ],
        validators=[InputRequired()],
    )
    admin_notes = TextAreaField("Admin notes", validators=[Optional(), Length(max=4000)])
    submit = SubmitField("Save complaint")


class ComplaintUpdateForm(FlaskForm):
    status = SelectField(
        "Status",
        choices=[
            (ComplaintStatus.OPEN, "Open"),
            (ComplaintStatus.IN_PROGRESS, "In progress"),
            (ComplaintStatus.RESOLVED, "Resolved"),
        ],
        validators=[InputRequired()],
    )
    admin_notes = TextAreaField("Admin notes", validators=[Optional(), Length(max=4000)])
    submit = SubmitField("Update")


class FeeCreateForm(FlaskForm):
    student_id = SelectField("Student", coerce=int, validators=[InputRequired()])
    academic_year_id = SelectField("Academic year", coerce=int, validators=[InputRequired()])
    fee_type_id = SelectField("Fee type", coerce=int, validators=[InputRequired()])
    amount_due = DecimalField(
        "Amount due", places=2, validators=[InputRequired(), NumberRange(min=0)]
    )
    due_date = DateField("Due date", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Create fee")


class FeeEditForm(FeeCreateForm):
    submit = SubmitField("Save fee")


class PaymentForm(FlaskForm):
    fee_id = HiddenField(validators=[Optional()])
    amount = DecimalField("Amount", places=2, validators=[InputRequired(), NumberRange(min=0.01)])
    paid_on = DateField("Paid on", validators=[InputRequired()])
    payment_method_id = SelectField("Method", coerce=int, validators=[InputRequired()])
    reference = StringField("Reference", validators=[Optional(), Length(max=100)])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Record payment")


class AttendanceForm(FlaskForm):
    latitude = HiddenField(validators=[InputRequired()])
    longitude = HiddenField(validators=[InputRequired()])
    accuracy = HiddenField(validators=[InputRequired()])
    submit = SubmitField("Mark attendance")


class AttendanceAdminForm(FlaskForm):
    attendance_date = DateField("Attendance date", validators=[InputRequired()])
    is_late = BooleanField("Late")
    submit = SubmitField("Save attendance")


class GeofenceForm(FlaskForm):
    name = StringField("Name", validators=[InputRequired(), Length(max=100)])
    latitude = DecimalField(
        "Latitude", places=7, validators=[InputRequired(), NumberRange(min=-90, max=90)]
    )
    longitude = DecimalField(
        "Longitude", places=7, validators=[InputRequired(), NumberRange(min=-180, max=180)]
    )
    radius_metres = DecimalField(
        "Radius (metres)", places=2, validators=[InputRequired(), NumberRange(min=1)]
    )
    max_accuracy_metres = DecimalField(
        "Maximum GPS accuracy (metres)", places=2, validators=[InputRequired(), NumberRange(min=1)]
    )
    check_in_start = TimeField("Check-in start", validators=[Optional()])
    check_in_end = TimeField("Check-in end", validators=[Optional()])
    late_after = TimeField("Late after", validators=[Optional()])
    timezone = StringField("Timezone", validators=[InputRequired(), Length(max=64)])
    active = BooleanField("Active")
    submit = SubmitField("Save geofence")


class MasterDataForm(FlaskForm):
    code = StringField("Code", validators=[InputRequired(), Length(max=60)])
    name = StringField("Name", validators=[InputRequired(), Length(max=160)])
    active = BooleanField("Active", default=True)
    submit = SubmitField("Save")


class EmptyForm(FlaskForm):
    submit = SubmitField("Confirm")
