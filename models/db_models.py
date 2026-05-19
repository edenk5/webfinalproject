"""
MODEL LAYER — db_models.py
Database schema in 3NF using Flask-SQLAlchemy.

Tables
------
User       — stores registered users with hashed passwords and a role.
Stock      — catalogue of supported stock tickers (managed by admins).
watchlist  — pure association table implementing the many-to-many
             relationship between User and Stock.

3NF compliance
--------------
• Every non-key column depends on the whole primary key only.
• No transitive dependencies exist between non-key columns.
• The 'watchlist' join table has no non-key attributes, satisfying 3NF
  trivially.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ── Single shared SQLAlchemy instance ────────────────────────────────────────
# Imported by app.py for init_app(), and by controllers that need DB access.
db = SQLAlchemy()


# ── Association table: User ↔ Stock (many-to-many) ───────────────────────────
# Pure join table — no extra columns → satisfies 3NF automatically.
watchlist_table = db.Table(
    "watchlist",
    db.Column("user_id",  db.Integer, db.ForeignKey("user.id"),  primary_key=True),
    db.Column("stock_id", db.Integer, db.ForeignKey("stock.id"), primary_key=True),
)


# ── User ──────────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    """
    Represents an application user.

    Columns
    -------
    id            — synthetic primary key.
    username      — unique login name (case-sensitive).
    password_hash — Werkzeug PBKDF2 hash; raw password is never stored.
    role          — 'user' (default) or 'admin'.
    """
    __tablename__ = "user"

    id            = db.Column(db.Integer,     primary_key=True)
    username      = db.Column(db.String(64),  unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(16),  nullable=False, default="user")

    # Many-to-many: a user's personal watchlist of Stock rows.
    watchlist = db.relationship(
        "Stock",
        secondary=watchlist_table,
        backref=db.backref("watchers", lazy="dynamic"),
        lazy="dynamic",
    )

    # ── helpers ──────────────────────────────────────────────────────────────
    def set_password(self, raw_password: str) -> None:
        """Hash and store the password — never persists the plaintext."""
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self) -> bool:
        """Convenience property used by the @admin_required decorator."""
        return self.role == "admin"

    def has_stock(self, ticker: str) -> bool:
        """Return True if this ticker is already in the user's watchlist."""
        return self.watchlist.filter_by(ticker=ticker.upper()).count() > 0

    def __repr__(self) -> str:
        return f"<User {self.username!r} role={self.role!r}>"


# ── Stock ─────────────────────────────────────────────────────────────────────
class Stock(db.Model):
    """
    Catalogue of stock tickers supported by the platform.
    Populated by admins; also auto-created when a user adds a ticker.

    Columns
    -------
    id           — synthetic primary key.
    ticker       — exchange symbol, always upper-case, unique.
    company_name — human-readable company name (nullable; filled from API).
    sector       — industry sector string (nullable).
    """
    __tablename__ = "stock"

    id           = db.Column(db.Integer,     primary_key=True)
    ticker       = db.Column(db.String(16),  unique=True, nullable=False, index=True)
    company_name = db.Column(db.String(128), nullable=True)
    sector       = db.Column(db.String(64),  nullable=True)

    def __repr__(self) -> str:
        return f"<Stock {self.ticker!r}>"
