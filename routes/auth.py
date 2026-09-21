from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func

from models import db, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("auth.after_login_redirect"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.after_login_redirect"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Case-insensitive so students can type their registration number
        # in any case (e.g. sit/swe/24/0003).
        user = User.query.filter(func.lower(User.username) == username.lower()).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.full_name}!", "success")
            return redirect(url_for("auth.after_login_redirect"))
        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/after-login")
@login_required
def after_login_redirect():
    if current_user.is_exam_officer():
        return redirect(url_for("admin.dashboard"))
    if current_user.is_student():
        return redirect(url_for("student.my_results"))
    return redirect(url_for("lecturer.dashboard"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


MIN_PASSWORD_LENGTH = 6


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if not current_user.check_password(current):
            flash("Your current password is incorrect.", "danger")
        elif len(new) < MIN_PASSWORD_LENGTH:
            flash(f"The new password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
        elif new != confirm:
            flash("The new password and its confirmation do not match.", "danger")
        else:
            current_user.set_password(new)
            db.session.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for("auth.after_login_redirect"))

    return render_template("change_password.html")
