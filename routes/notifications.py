from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from services.security_service import user_required
from services.notification_service import NotificationService
from services.notification_rules import safe_internal_link

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/notifications")
@login_required
@user_required
def index():
    user_id = current_user.user_id
    unread_only = request.args.get("filter") == "unread"
    NotificationService.refresh(user_id)
    return render_template(
        "notifications/index.html",
        items=NotificationService.list_for_user(user_id, unread_only=unread_only),
        prefs=NotificationService.get_preferences(user_id),
        unread_only=unread_only,
    )


@notifications_bp.route("/notifications/<int:notification_id>/open", methods=["POST"])
@login_required
@user_required
def open_notification(notification_id: int):
    n = NotificationService.mark_read(current_user.user_id, notification_id)
    if not n:
        flash("Notification not found.", "warning")
        return redirect(url_for("notifications.index"))
    return redirect(safe_internal_link(n.link))


@notifications_bp.route("/notifications/read-all", methods=["POST"])
@login_required
@user_required
def read_all():
    count = NotificationService.mark_all_read(current_user.user_id)
    flash(f"Marked {count} notification(s) as read.", "info")
    return redirect(url_for("notifications.index"))


@notifications_bp.route("/notifications/clear", methods=["POST"])
@login_required
@user_required
def clear():
    count = NotificationService.clear_read(current_user.user_id)
    flash(f"Removed {count} read notification(s).", "info")
    return redirect(url_for("notifications.index"))


@notifications_bp.route("/notifications/settings", methods=["POST"])
@login_required
@user_required
def settings():
    if NotificationService.update_preferences(current_user.user_id, request.form):
        flash("Notification preferences saved.", "success")
    else:
        flash("Please enter a valid reminder time (HH:MM, 24-hour).", "danger")
    return redirect(url_for("notifications.index") + "#settings")
