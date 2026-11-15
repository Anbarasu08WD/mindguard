from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models.mood import MoodRecord
from models.journal import JournalEntry
from services.analytics_service import AnalyticsService, MOOD_SCORE_MAP
from services.recommendation_service import RecommendationService
from services.encryption_service import EncryptionService
from services.insight_service import InsightService
from services.security_service import user_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
@user_required
def index():
    user_id = current_user.user_id
    today = date.today()

    # Retrieve today's mood record if existing
    today_record = MoodRecord.query.filter_by(user_id=user_id, recorded_at=today).first()

    # Retrieve recent 7-day stats for trend
    analytics = AnalyticsService.get_user_analytics(user_id=user_id, days=7)

    # Retrieve recent journal entries (decrypted for owner)
    recent_journals = (
        JournalEntry.query.filter_by(user_id=user_id)
        .order_by(JournalEntry.created_at.desc())
        .limit(3)
        .all()
    )

    decrypted_recent_journals = []
    for entry in recent_journals:
        decrypted_recent_journals.append({
            "journal_id": entry.journal_id,
            "title": entry.title,
            "snippet": EncryptionService.decrypt(entry.encrypted_content)[:120] + "...",
            "created_at": entry.created_at,
        })

    # Retrieve top suggestions
    suggestions_data = RecommendationService.get_personalized_suggestions(user_id=user_id)

    return render_template(
        "dashboard/index.html",
        today=today,
        today_record=today_record,
        analytics=analytics,
        recent_journals=decrypted_recent_journals,
        suggestions=suggestions_data["recommended"][:3],
        notes=suggestions_data["notes"],
        top_insight=InsightService.top_insight(user_id),
    )
