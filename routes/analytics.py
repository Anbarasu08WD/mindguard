import csv
import io
from datetime import date, timedelta
from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user
from models.mood import MoodRecord
from services.analytics_service import AnalyticsService, MOOD_SCORE_MAP
from services.audit_service import AuditService
from services.security_service import user_required
from timeutil import local_today

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics")
@login_required
@user_required
def index():
    user_id = current_user.user_id
    days = request.args.get("days", 7, type=int)
    if days not in [7, 30, 90]:
        days = 7

    analytics = AnalyticsService.get_user_analytics(user_id=user_id, days=days)
    return render_template("analytics/index.html", analytics=analytics, selected_days=days)


@analytics_bp.route("/api/analytics/weekly")
@login_required
@user_required
def api_weekly():
    data = AnalyticsService.get_user_analytics(user_id=current_user.user_id, days=7)
    return jsonify(data)


@analytics_bp.route("/api/analytics/monthly")
@login_required
@user_required
def api_monthly():
    data = AnalyticsService.get_user_analytics(user_id=current_user.user_id, days=30)
    return jsonify(data)


@analytics_bp.route("/api/analytics/custom")
@login_required
@user_required
def api_custom():
    days = request.args.get("days", 7, type=int)
    if days not in [7, 30, 90]:
        days = 7
    data = AnalyticsService.get_user_analytics(user_id=current_user.user_id, days=days)
    return jsonify(data)


@analytics_bp.route("/analytics/export.csv")
@login_required
@user_required
def export_csv():
    """Download the signed-in user's own mood check-ins for the chosen window as CSV.

    Free-text notes are intentionally left out. Row-Level Security still limits
    the query to the current user's rows.
    """
    days = request.args.get("days", 30, type=int)
    if days not in [7, 30, 90]:
        days = 30
    start = local_today() - timedelta(days=days - 1)

    records = (
        MoodRecord.query.filter(
            MoodRecord.user_id == current_user.user_id,
            MoodRecord.recorded_at >= start,
        )
        .order_by(MoodRecord.recorded_at.asc())
        .all()
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["date", "mood", "mood_score", "stress_level", "energy_level"])
    for r in records:
        writer.writerow([
            r.recorded_at.isoformat(),
            r.mood,
            MOOD_SCORE_MAP.get(r.mood, 3),
            r.stress_level,
            r.energy_level,
        ])

    AuditService.log_event("MOOD_DATA_EXPORTED", "SUCCESS", current_user.user_id)
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=mindguard_mood_last_{days}_days.csv"},
    )
