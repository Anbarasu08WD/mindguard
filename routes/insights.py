from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from services.security_service import user_required
from services.insight_service import InsightService
from services.audit_service import AuditService

insights_bp = Blueprint("insights", __name__)


@insights_bp.route("/insights")
@login_required
@user_required
def index():
    uid = current_user.user_id
    return render_template(
        "insights/index.html",
        data=InsightService.overview(uid),
        reports=InsightService.list_reports(uid),
    )


@insights_bp.route("/insights/report", methods=["POST"])
@login_required
@user_required
def generate_report():
    InsightService.save_weekly_report(current_user.user_id)
    AuditService.log_event("WELLNESS_REPORT_GENERATED", "SUCCESS", current_user.user_id)
    flash("Your weekly wellness report was saved.", "success")
    return redirect(url_for("insights.index"))
