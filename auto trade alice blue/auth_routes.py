# auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)

from models import db, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login for AlgoSphere app."""
    if request.method == "GET":
        # If already logged in, go straight to dashboard
        if current_user.is_authenticated:
            return redirect(url_for("dash.dashboard"))
        return render_template("login.html")

    # POST: process form
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()

    if not email or not password:
        flash("Email and password are required.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        flash("Invalid email or password.", "danger")
        return redirect(url_for("auth.login"))

    login_user(user)
    flash("Logged in successfully.", "success")
    return redirect(url_for("dash.dashboard"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Simple email/password registration."""
    if request.method == "GET":
        return render_template("register.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()
    confirm = request.form.get("confirm", "").strip()

    if not email or not password or not confirm:
        flash("All fields are required.", "danger")
        return redirect(url_for("auth.register"))

    if password != confirm:
        flash("Passwords do not match.", "danger")
        return redirect(url_for("auth.register"))

    existing = User.query.filter_by(email=email).first()
    if existing:
        flash("An account with this email already exists.", "warning")
        return redirect(url_for("auth.login"))

    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    flash("Account created. Please log in.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
@login_required
def logout():
    """Log the user out and return to login page."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
