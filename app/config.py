from __future__ import annotations

import os
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
IS_VERCEL = bool(os.getenv("VERCEL"))


class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Kolkata")

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "dev-only-change-me",
    )

    # ---------------------------------------------------------
    # Writable Flask instance directory
    # ---------------------------------------------------------

    if IS_VERCEL:
        INSTANCE_PATH = Path(tempfile.gettempdir()) / "des-hostel-instance"
    else:
        INSTANCE_PATH = BASE_DIR / "instance"

    # ---------------------------------------------------------
    # Database
    # ---------------------------------------------------------

    _database_url = os.getenv("DATABASE_URL", "").strip()

    # Some PostgreSQL providers may still provide postgres://
    if _database_url.startswith("postgres://"):
        _database_url = _database_url.replace(
            "postgres://",
            "postgresql://",
            1,
        )

    if _database_url:
        SQLALCHEMY_DATABASE_URI = _database_url

    elif IS_VERCEL:
        # TEMPORARY fallback only.
        # Data stored here is NOT persistent across Vercel instances.
        SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/hostel.db"

    else:
        # Local development SQLite database
        SQLALCHEMY_DATABASE_URI = "sqlite:///hostel.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # ---------------------------------------------------------
    # Password reset
    # ---------------------------------------------------------

    PASSWORD_RESET_TTL_MINUTES = int(
        os.getenv("PASSWORD_RESET_TTL_MINUTES", "30")
    )

    PASSWORD_RESET_SHOW_LINK = os.getenv(
        "PASSWORD_RESET_SHOW_LINK",
        "1" if APP_ENV == "development" else "0",
    ).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    # ---------------------------------------------------------
    # Mail
    # ---------------------------------------------------------

    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")

    MAIL_USE_TLS = os.getenv(
        "MAIL_USE_TLS",
        "1",
    ).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    MAIL_DEFAULT_SENDER = os.getenv(
        "MAIL_DEFAULT_SENDER",
        "",
    )

    MAIL_TIMEOUT = float(
        os.getenv("MAIL_TIMEOUT", "10")
    )

    MAIL_SUPPRESS_SEND = os.getenv(
        "MAIL_SUPPRESS_SEND",
        "0",
    ).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    # ---------------------------------------------------------
    # Instance directory
    # ---------------------------------------------------------

    @classmethod
    def ensure_instance(cls) -> str:
        """
        Create and return a writable Flask instance directory.

        Local:
            <project>/instance

        Vercel:
            /tmp/des-hostel-instance
        """

        instance_path = cls.INSTANCE_PATH

        instance_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return str(instance_path)
