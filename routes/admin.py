from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, Response
from flask_login import login_required, current_user
from sqlalchemy import text
from extensions import db
from models.user import User
from models.audit import AuditLog
from services.security_service import admin_required
from services.audit_service import AuditService
from services.admin_stats import AdminStatsService
from services.admin_utils import parse_date_param, clamp_page, audit_rows_to_csv
from datetime import datetime, timedelta

AUDIT_PAGE_SIZE = 25

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@login_required
@admin_required
def index():
    # Aggregated system metrics (accounts and audit data only, never wellness records)
    summary = AdminStatsService.user_summary()
    total_users = summary["total"]
    active_users = summary["active"]
    disabled_users = summary["disabled"]
    failed_logins = AdminStatsService.failed_login_count()

    recent_security_events = (
        AuditLog.query.order_by(AuditLog.timestamp.desc())
        .limit(8)
        .all()
    )
    signup_labels, signup_values = AdminStatsService.signups_by_day(14)
    event_labels, event_values = AdminStatsService.security_events_by_day(14)
    top_actions = AdminStatsService.top_actions(30, 8)
    rls = AdminStatsService.rls_health()

    # Check database health
    db_healthy = False
    db_version = "Unknown"
    try:
        res = db.session.execute(text("SELECT version();")).scalar()
        if res:
            db_healthy = True
            db_version = res.split(" on ")[0]
    except Exception as e:
        db_healthy = False

    return render_template(
        "admin/index.html",
        total_users=total_users,
        active_users=active_users,
        disabled_users=disabled_users,
        failed_logins=failed_logins,
        recent_security_events=recent_security_events,
        db_healthy=db_healthy,
        db_version=db_version,
        summary=summary,
        rls=rls,
        top_actions=top_actions,
        chart_data={
            "signups": {"labels": signup_labels, "values": signup_values},
            "events": {"labels": event_labels, "values": event_values},
        },
    )


@admin_bp.route("/admin/users")
@login_required
@admin_required
def users():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = User.query

    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )

    if status_filter:
        query = query.filter(User.account_status == status_filter)

    users_list = query.order_by(User.created_at.desc()).all()

    return render_template(
        "admin/users.html",
        users=users_list,
        search=search,
        status_filter=status_filter,
    )


@admin_bp.route("/admin/user/toggle/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def toggle_user(user_id: int):
    # Prevent admin from deactivating themselves
    if user_id == current_user.user_id:
        flash("You cannot deactivate your own administrative account.", "warning")
        return redirect(url_for("admin.users"))

    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    new_status = "disabled" if user.account_status == "active" else "active"

    try:
        result = db.session.execute(
            text("""
                SELECT user_id, email, account_status
                FROM public.auth_set_user_status(
                    :target_user_id,
                    :new_status
                )
            """),
            {
                "target_user_id": user_id,
                "new_status": new_status,
            },
        ).one_or_none()

        db.session.commit()

        if not result:
            flash("User status could not be updated.", "danger")
            return redirect(url_for("admin.users"))

    except Exception:
        db.session.rollback()
        flash("Unable to update the account status.", "danger")
        return redirect(url_for("admin.users"))

    AuditService.log_event(
        action=f"ADMIN_ACCOUNT_{new_status.upper()}",
        event_status="SUCCESS",
        user_id=current_user.user_id,
    )

    flash(f"Account for {result.email} is now {result.account_status}.", "info")
    return redirect(url_for("admin.users"))

def _filtered_audit_query():
    action_filter = request.args.get("action", "").strip()
    status_filter = request.args.get("status", "").strip()
    date_from = parse_date_param(request.args.get("from", ""))
    date_to = parse_date_param(request.args.get("to", ""))

    query = AuditLog.query
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    if status_filter:
        query = query.filter(AuditLog.event_status == status_filter)
    if date_from:
        query = query.filter(AuditLog.timestamp >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(AuditLog.timestamp < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    return query, action_filter, status_filter, date_from, date_to


@admin_bp.route("/admin/audit-logs")
@login_required
@admin_required
def audit_logs():
    query, action_filter, status_filter, date_from, date_to = _filtered_audit_query()
    total = query.count()
    page, total_pages = clamp_page(request.args.get("page", 1), total, AUDIT_PAGE_SIZE)

    logs = (
        query.order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * AUDIT_PAGE_SIZE).limit(AUDIT_PAGE_SIZE).all()
    )
    filter_args = {k: v for k, v in {
        "action": action_filter, "status": status_filter,
        "from": date_from.isoformat() if date_from else "",
        "to": date_to.isoformat() if date_to else "",
    }.items() if v}

    return render_template(
        "admin/audit_logs.html",
        logs=logs,
        action_filter=action_filter,
        status_filter=status_filter,
        date_from=date_from.isoformat() if date_from else "",
        date_to=date_to.isoformat() if date_to else "",
        page=page,
        total_pages=total_pages,
        total=total,
        filter_args=filter_args,
    )


@admin_bp.route("/admin/audit-logs/export.csv")
@login_required
@admin_required
def audit_logs_export():
    """Export the filtered audit trail (max 5000 rows). Audit logs hold no wellness content."""
    query, *_ = _filtered_audit_query()
    rows = query.order_by(AuditLog.timestamp.desc()).limit(5000).all()
    AuditService.log_event("ADMIN_AUDIT_EXPORTED", "SUCCESS", current_user.user_id)
    return Response(
        audit_rows_to_csv(rows),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=mindguard_audit_logs.csv"},
    )
