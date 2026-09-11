from __future__ import annotations

from flask import Flask, render_template

from app.commands import register_commands
from app.config import Config
from app.extensions import csrf, db, login_manager, migrate


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    config_object.ensure_instance(app.instance_path)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."

    from app import models  # noqa: F401
    from app.admin import bp as admin_bp
    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.student import bp as student_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    register_commands(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        if not user_id.isdigit():
            return None
        return db.session.get(models.User, int(user_id))

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(self), camera=(), microphone=()"
        )
        return response

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
