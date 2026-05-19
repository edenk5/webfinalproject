"""
CONTROLLER LAYER — AuthController (Flask Blueprint)
Responsible for: user registration, login, logout, admin panel,
and DB-backed watchlist add/remove actions.

Routes
------
GET/POST  /login                — authenticate a user
GET/POST  /register             — create a new standard user account
GET       /logout               — end the current session
GET/POST  /admin                — admin-only: manage Stock catalogue
POST      /watchlist/add/<t>    — add a ticker to the logged-in user's DB watchlist
POST      /watchlist/remove/<t> — remove a ticker from the DB watchlist
"""

import functools
from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, abort
)
from flask_login import (
    login_user, logout_user, login_required, current_user
)

from models.db_models import db, User, Stock

auth_bp = Blueprint("auth", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Custom decorator: @admin_required
# ─────────────────────────────────────────────────────────────────────────────
def admin_required(f):
    """
    Decorator that ensures the current user is logged in AND has role='admin'.
    Usage:
        @auth_bp.route("/admin")
        @admin_required
        def admin_panel(): ...
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in first.", "info")
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            abort(403)          # HTTP 403 Forbidden for non-admins
        return f(*args, **kwargs)
    return decorated_function


# ─────────────────────────────────────────────────────────────────────────────
# Route: Register  /register
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Create a new standard user account."""
    if current_user.is_authenticated:
        return redirect(url_for("stocks.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        # ── Validation ──────────────────────────────────────────────────────
        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("register.html")

        if len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("That username is already taken. Please choose another.", "error")
            return render_template("register.html")

        # ── Create and persist the user ──────────────────────────────────────
        user = User(username=username, role="user")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(f"Account created for '{username}'! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ─────────────────────────────────────────────────────────────────────────────
# Route: Login  /login
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate an existing user and start a session."""
    if current_user.is_authenticated:
        return redirect(url_for("stocks.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.username}! 👋", "success")
            # Honour the ?next= redirect set by @login_required
            next_page = request.args.get("next")
            return redirect(next_page or url_for("stocks.dashboard"))

        flash("Invalid username or password. Please try again.", "error")

    return render_template("login.html")


# ─────────────────────────────────────────────────────────────────────────────
# Route: Logout  /logout
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/logout")
@login_required
def logout():
    """End the current user session."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("stocks.dashboard"))


# ─────────────────────────────────────────────────────────────────────────────
# Route: Admin Panel  /admin
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_panel():
    """
    Admin-only panel.
    GET  — list all Stock rows in the DB.
    POST — add a new supported ticker to the Stock catalogue.
    """
    if request.method == "POST":
        ticker       = request.form.get("ticker", "").strip().upper()
        company_name = request.form.get("company_name", "").strip() or None
        sector       = request.form.get("sector", "").strip() or None

        if not ticker:
            flash("Ticker symbol is required.", "error")
        elif Stock.query.filter_by(ticker=ticker).first():
            flash(f"{ticker} is already in the catalogue.", "warning")
        else:
            stock = Stock(ticker=ticker, company_name=company_name, sector=sector)
            db.session.add(stock)
            db.session.commit()
            flash(f"✅ {ticker} added to the stock catalogue.", "success")

    all_stocks = Stock.query.order_by(Stock.ticker).all()
    return render_template("admin.html", stocks=all_stocks)


# ─────────────────────────────────────────────────────────────────────────────
# Route: Watchlist Add  /watchlist/add/<ticker>
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/watchlist/add/<ticker>", methods=["POST"])
@login_required
def watchlist_add(ticker: str):
    """Add a ticker to the current user's personal DB watchlist."""
    ticker = ticker.upper()

    # Get or create the Stock row in the catalogue
    stock = Stock.query.filter_by(ticker=ticker).first()
    if not stock:
        stock = Stock(ticker=ticker)
        db.session.add(stock)
        db.session.flush()      # get an id without committing yet

    if not current_user.has_stock(ticker):
        current_user.watchlist.append(stock)
        db.session.commit()
        flash(f"✅ {ticker} added to your watchlist.", "success")
    else:
        flash(f"{ticker} is already in your watchlist.", "info")

    # Return to wherever the user came from
    return redirect(request.referrer or url_for("stocks.watchlist"))


# ─────────────────────────────────────────────────────────────────────────────
# Route: Watchlist Remove  /watchlist/remove/<ticker>
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route("/watchlist/remove/<ticker>", methods=["POST"])
@login_required
def watchlist_remove(ticker: str):
    """Remove a ticker from the current user's personal DB watchlist."""
    ticker = ticker.upper()
    stock  = Stock.query.filter_by(ticker=ticker).first()

    if stock and current_user.has_stock(ticker):
        current_user.watchlist.remove(stock)
        db.session.commit()
        flash(f"🗑️ {ticker} removed from your watchlist.", "info")
    else:
        flash(f"{ticker} was not found in your watchlist.", "warning")

    return redirect(request.referrer or url_for("stocks.watchlist"))
