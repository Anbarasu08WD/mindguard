import re
from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user
from services.audit_service import AuditService


def admin_required(f):
    """Decorator to restrict view access to Administrator accounts only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            AuditService.log_event(
                action="UNAUTHORIZED_ADMIN_ACCESS_ATTEMPT",
                event_status="DENIED",
                user_id=current_user.user_id,
            )
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def user_required(f):
    """Decorator to restrict access to authenticated active standard users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_active:
            flash("Your account has been deactivated. Please contact an administrator.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


class SecurityService:
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """
        Validates password meets security requirements:
        - Minimum 8 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 digit
        - At least 1 special character
        """
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter."
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter."
        if not re.search(r"\d", password):
            return False, "Password must contain at least one number."
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+/\\\[\]]", password):
            return False, "Password must contain at least one special character."
        return True, "Password meets strength criteria."
