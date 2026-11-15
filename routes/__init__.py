from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.mood import mood_bp
from routes.journal import journal_bp
from routes.analytics import analytics_bp
from routes.suggestions import suggestions_bp
from routes.privacy import privacy_bp
from routes.profile import profile_bp
from routes.admin import admin_bp
from routes.notifications import notifications_bp
from routes.insights import insights_bp

__all__ = [
    "auth_bp",
    "dashboard_bp",
    "mood_bp",
    "journal_bp",
    "analytics_bp",
    "suggestions_bp",
    "privacy_bp",
    "profile_bp",
    "admin_bp",
    "notifications_bp",
    "insights_bp",
]
