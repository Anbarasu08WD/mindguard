from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models.user import User
from models.session import UserSession
from services.security_service import SecurityService, user_required
from services.audit_service import AuditService
from services.notification_service import NotificationService

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile")
@login_required
def index():
    user = db.session.get(User, current_user.user_id)
    active_sessions = (
        UserSession.query.filter_by(user_id=user.user_id, revoked_at=None)
        .order_by(UserSession.created_at.desc())
        .all()
    )
    return render_template("profile/index.html", user=user, sessions=active_sessions)


@profile_bp.route("/profile/update", methods=["POST"])
@login_required
def update():
    full_name = request.form.get("full_name", "").strip()

    if not full_name:
        flash("Full name cannot be empty.", "danger")
        return redirect(url_for("profile.index"))

    try:
        user = db.session.get(User, current_user.user_id)
        user.full_name = full_name
        db.session.commit()
        AuditService.log_event("PROFILE_UPDATE", "SUCCESS", user.user_id)
        flash("Profile updated successfully.", "success")
    except Exception:
        db.session.rollback()
        flash("Error updating profile.", "danger")

    return redirect(url_for("profile.index"))


@profile_bp.route("/profile/change-password", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_new_password = request.form.get("confirm_new_password", "")

    user = db.session.get(User, current_user.user_id)

    if not user.check_password(current_password):
        AuditService.log_event("PASSWORD_CHANGE_BAD_CURRENT_PASSWORD", "FAILED", user.user_id)
        flash("Incorrect current password.", "danger")
        return redirect(url_for("profile.index"))

    if new_password != confirm_new_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("profile.index"))

    is_strong, msg = SecurityService.validate_password_strength(new_password)
    if not is_strong:
        flash(msg, "danger")
        return redirect(url_for("profile.index"))

    try:
        user.set_password(new_password)
        db.session.commit()
        AuditService.log_event("PASSWORD_CHANGED", "SUCCESS", user.user_id)
        NotificationService.notify_security(
            user.user_id, "Password changed",
            "Your MindGuard password was changed. If this was not you, contact an administrator.",
        )
        flash("Password updated successfully. Please log in with your new password next time.", "success")
    except Exception:
        db.session.rollback()
        flash("Could not update password. Please try again.", "danger")

    return redirect(url_for("profile.index"))


@profile_bp.route("/profile/revoke-session/<int:session_id>", methods=["POST"])
@login_required
def revoke_session(session_id: int):
    sess = UserSession.query.filter_by(session_id=session_id, user_id=current_user.user_id).first()
    if sess:
        sess.revoked_at = datetime.now(timezone.utc)
        db.session.commit()
        AuditService.log_event("SESSION_REVOKED", "SUCCESS", current_user.user_id)
        flash("Session revoked.", "info")
    return redirect(url_for("profile.index"))
