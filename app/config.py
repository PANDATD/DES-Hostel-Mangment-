from __future__ import annotations

import os
from pathlib import Path


class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Kolkata")

    _database_url = os.getenv("DATABASE_URL", "").strip()
    SQLALCHEMY_DATABASE_URI = _database_url or "sqlite:///hostel.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    PASSWORD_RESET_TTL_MINUTES = int(os.getenv("PASSWORD_RESET_TTL_MINUTES", "30"))
    PASSWORD_RESET_SHOW_LINK = os.getenv(
        "PASSWORD_RESET_SHOW_LINK", "1" if APP_ENV == "development" else "0"
    ).lower() in {"1", "true", "yes", "on"}

    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "1").lower() in {"1", "true", "yes", "on"}
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "")
    MAIL_TIMEOUT = float(os.getenv("MAIL_TIMEOUT", "10"))
    MAIL_SUPPRESS_SEND = os.getenv("MAIL_SUPPRESS_SEND", "0").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    @staticmethod
    def ensure_instance(instance_path: str) -> None:
        Path(instance_path).mkdir(parents=True, exist_ok=True)
