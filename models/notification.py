from datetime import datetime, timezone
from extensions import db


class Notification(db.Model):
    """In-app notification. Text must never contain mood notes or journal content."""
    __tablename__ = "notifications"

    notification_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    category = db.Column(db.String(30), nullable=False)   # reminder | streak | weekly | insight | security
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    link = db.Column(db.String(200), nullable=True)        # internal path only, e.g. /mood/add
    dedupe_key = db.Column(db.String(120), nullable=True)  # makes generation idempotent
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "dedupe_key", name="uq_notification_dedupe"),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.notification_id} user={self.user_id} cat={self.category}>"


class NotificationPreference(db.Model):
    __tablename__ = "notification_preferences"

    pref_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    daily_reminder = db.Column(db.Boolean, nullable=False, default=True)
    reminder_time = db.Column(db.String(5), nullable=False, default="20:00")  # HH:MM, server local time
    streak_alerts = db.Column(db.Boolean, nullable=False, default=True)
    weekly_summary = db.Column(db.Boolean, nullable=False, default=True)
    security_alerts = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
