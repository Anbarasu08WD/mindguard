import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, limiter
from models import user
from models.user import User
from models.consent import UserConsent
from models.session import UserSession
from services.audit_service import AuditService
from services.database_security import set_explicit_rls_user
from services.security_service import SecurityService

auth_bp = Blueprint("auth", __name__)
def lookup_user_for_login(email):
    result = db.session.execute(
        db.text(
            "SELECT public.auth_lookup_user(:email)"
        ),
        {"email": email}
    ).scalar_one_or_none()

    if not result:
        return None

    return User(
        user_id=result["user_id"],
        full_name=result["full_name"],
        email=result["email"],
        password_hash=result["password_hash"],
        role=result["role"],
        account_status=result["account_status"]
    )

@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("15 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        consent_privacy = request.form.get("consent_privacy")

        # Validation
        if not full_name or not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template("auth/register.html", full_name=full_name, email=email)

        if not consent_privacy:
            flash("You must agree to the Privacy Policy and Consent Terms to register.", "warning")
            return render_template("auth/register.html", full_name=full_name, email=email)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html", full_name=full_name, email=email)

        is_strong, msg = SecurityService.validate_password_strength(password)
        if not is_strong:
            flash(msg, "danger")
            return render_template("auth/register.html", full_name=full_name, email=email)

        # Check existing email
        existing_user = db.session.execute(
            db.text("SELECT public.auth_email_exists(:email)"),
            {"email": email}
        ).scalar_one()
        if existing_user:
            flash("An account with that email address already exists. Please log in.", "warning")
            return redirect(url_for("auth.login"))

        try:
            # Create user
            user = User(
                full_name=full_name,
                email=email,
                role="user",
                account_status="active"
            )
            user.set_password(password)

# Reserve the user ID before insertion so RLS context
# can be established before the INSERT statement.
            user.user_id = db.session.execute(
                db.text(
                    "SELECT nextval(pg_get_serial_sequence('public.users', 'user_id'))"
                )
            ).scalar_one()

            set_explicit_rls_user(user.user_id)

            db.session.add(user)
            db.session.flush()

            # Record initial consent
            consent = UserConsent(
                user_id=user.user_id,
                consent_type="privacy_policy",
                consent_status="GRANTED"
            )
            db.session.add(consent)
            db.session.commit()

            AuditService.log_event("USER_REGISTRATION", "SUCCESS", user.user_id)
            flash("Registration successful! You can now log in to your secure account.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", "danger")

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.index"))
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("auth/login.html", email=email)

        user = lookup_user_for_login(email)

        if user and user.check_password(password):
            if user.account_status != "active":
                AuditService.log_event("LOGIN_ATTEMPT_DISABLED_ACCOUNT", "DENIED", user.user_id)
                flash("Your account has been deactivated. Please contact an administrator.", "danger")
                return render_template("auth/login.html", email=email)

            login_user(user, remember=remember)
            from services.database_security import set_explicit_rls_user, clear_explicit_rls_user
            set_explicit_rls_user(user.user_id)

            # Record active session token hash in user_sessions
            raw_token = secrets.token_hex(32)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            session_lifetime = timedelta(days=14 if remember else 1)
            expires_at = datetime.now(timezone.utc) + session_lifetime

            user_session_record = UserSession(
                user_id=user.user_id,
                session_token_hash=token_hash,
                expires_at=expires_at
            )
            db.session.add(user_session_record)
            db.session.commit()

            session["session_record_id"] = user_session_record.session_id
            AuditService.log_event("USER_LOGIN", "SUCCESS", user.user_id)

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for("admin.index"))
            return redirect(url_for("dashboard.index"))
        else:
            # Safe generic failure message; prevents user enumeration
            AuditService.log_event("LOGIN_FAILURE_BAD_CREDENTIALS", "FAILED", user.user_id if user else None)
            flash("Invalid email address or password.", "danger")

    return render_template("auth/login.html")



@auth_bp.route("/logout")
@login_required
def logout():
    uid = current_user.user_id

    # Revoke database session record if present
    sess_id = session.get("session_record_id")
    if sess_id:
        sess_rec = UserSession.query.filter_by(
            session_id=sess_id,
            user_id=uid
        ).first()

        if sess_rec:
            sess_rec.revoked_at = datetime.now(timezone.utc)
            db.session.commit()

    AuditService.log_event("USER_LOGOUT", "SUCCESS", uid)

    # Clear the Flask session BEFORE Flask-Login logout
    session.clear()
    logout_user()

    flash("You have been securely logged out.", "info")
    return redirect(url_for("auth.login"))
