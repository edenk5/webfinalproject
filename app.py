"""
ENTRY POINT — app.py
Only job: create the Flask app, configure extensions, and register blueprints.
Business logic lives in models/, routing in controllers/.
"""

import os
from flask import Flask
from flask_login import LoginManager

from models.db_models import db, User
from controllers.stock_controller import stock_bp
from controllers.auth_controller import auth_bp

# ── Flask-Login setup (module-level so auth_controller can import it) ─────────
login_manager = LoginManager()
login_manager.login_view = "auth.login"          # redirect here when @login_required
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Flask-Login hook: reload the User from the DB on each request."""
    return db.session.get(User, int(user_id))


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # ── Configuration ──────────────────────────────────────────────────────────
    app.secret_key = os.environ.get("SECRET_KEY", "stockadvisor-secret-2024")
    basedir = os.path.abspath(os.path.dirname(__file__))
    # ── Database Configuration (Cloud PostgreSQL) ──────────────────────────────
    # Replace 'sqlite://...' with a cloud Postgres connection string from Neon, Aiven, or Heroku.
    # We fetch this from the 'DATABASE_URL' environment variable.
    database_url = os.environ.get("DATABASE_URL")
    
    if database_url:
        # Fix for SQLAlchemy 1.4+ which dropped support for 'postgres://' (common in cloud providers)
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    else:
        # Fallback to local SQLite if no cloud database is configured
        print("⚠️ WARNING: No DATABASE_URL found. Falling back to local SQLite database.")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(basedir, 'stockadvisor.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ── Init extensions ────────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)

    # ── Register blueprints ────────────────────────────────────────────────────
    app.register_blueprint(stock_bp)    # dashboard, detail, watchlist, API
    app.register_blueprint(auth_bp)     # login, register, logout, admin

    # ── Create DB tables (safe to call multiple times) ─────────────────────────
    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5050)