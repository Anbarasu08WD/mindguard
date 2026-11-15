from datetime import date, datetime, timedelta
from typing import Dict, List

from extensions import db
from models.mood import MoodRecord
from models.notification import Notification, NotificationPreference
from services.analytics_utils import calculate_streaks
from services.notification_rules import due_notifications, parse_hhmm, safe_internal_link

PREF_FIELDS = ("daily_reminder", "streak_alerts", "weekly_summary", "security_alerts")


class NotificationService:
    # ---------------------------- preferences ----------------------------
    @staticmethod
    def get_preferences(user_id: int) -> NotificationPreference:
        pref = NotificationPreference.query.filter_by(user_id=user_id).first()
        if not pref:
            pref = NotificationPreference(user_id=user_id)
            db.session.add(pref)
            db.session.commit()
        return pref

    @staticmethod
    def update_preferences(user_id: int, form) -> bool:
        """Update from a submitted form. Returns False if the reminder time is invalid."""
        pref = NotificationService.get_preferences(user_id)
        reminder_time = (form.get("reminder_time") or "").strip()
        if parse_hhmm(reminder_time) is None:
            return False
        pref.reminder_time = reminder_time
        for field in PREF_FIELDS:
            setattr(pref, field, form.get(field) == "on")
        db.session.commit()
        return True

    # ---------------------------- creation ----------------------------
    @staticmethod
    def create(user_id: int, category: str, title: str, message: str,
               link: str = None, dedupe_key: str = None) -> bool:
        """Create a notification. Returns False when it already exists."""
        if dedupe_key and Notification.query.filter_by(user_id=user_id, dedupe_key=dedupe_key).first():
            return False
        db.session.add(Notification(
            user_id=user_id, category=category, title=title[:150], message=message[:300],
            link=safe_internal_link(link) if link else None, dedupe_key=dedupe_key,
        ))
        db.session.commit()
        return True

    @staticmethod
    def notify_security(user_id: int, title: str, message: str) -> None:
        pref = NotificationService.get_preferences(user_id)
        if pref.security_alerts:
            NotificationService.create(user_id, "security", title, message, "/profile")

    @staticmethod
    def refresh(user_id: int, now: datetime = None) -> int:
        """Create any notifications that are due for this user. Returns how many were created."""
        now = now or datetime.now()
        today = now.date()
        pref = NotificationService.get_preferences(user_id)

        lifetime_dates = [r[0] for r in db.session.query(MoodRecord.recorded_at)
                          .filter(MoodRecord.user_id == user_id).all()]
        has_today = today in lifetime_dates
        current_streak, _ = calculate_streaks(lifetime_dates, today)
        last7 = sum(1 for d in lifetime_dates if (today - d).days < 7)

        since = now - timedelta(days=10)
        existing = {
            k for (k,) in db.session.query(Notification.dedupe_key)
            .filter(Notification.user_id == user_id, Notification.created_at >= since,
                    Notification.dedupe_key.isnot(None)).all()
        }

        created = 0
        for item in due_notifications(
            today=today, now=now.time(),
            prefs={
                "daily_reminder": pref.daily_reminder, "reminder_time": pref.reminder_time,
                "streak_alerts": pref.streak_alerts, "weekly_summary": pref.weekly_summary,
            },
            has_checkin_today=has_today, current_streak=current_streak,
            entries_last_7_days=last7, existing_keys=existing,
        ):
            if NotificationService.create(user_id, item["category"], item["title"],
                                          item["message"], item["link"], item["dedupe_key"]):
                created += 1
        return created

    # ---------------------------- reading / updating ----------------------------
    @staticmethod
    def unread_count(user_id: int) -> int:
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def latest(user_id: int, limit: int = 5) -> List[Notification]:
        return (Notification.query.filter_by(user_id=user_id)
                .order_by(Notification.created_at.desc()).limit(limit).all())

    @staticmethod
    def list_for_user(user_id: int, unread_only: bool = False, limit: int = 100) -> List[Notification]:
        q = Notification.query.filter_by(user_id=user_id)
        if unread_only:
            q = q.filter_by(is_read=False)
        return q.order_by(Notification.created_at.desc()).limit(limit).all()

    @staticmethod
    def mark_read(user_id: int, notification_id: int):
        n = Notification.query.filter_by(user_id=user_id, notification_id=notification_id).first()
        if n and not n.is_read:
            n.is_read = True
            db.session.commit()
        return n

    @staticmethod
    def mark_all_read(user_id: int) -> int:
        n = Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
        db.session.commit()
        return n

    @staticmethod
    def clear_read(user_id: int) -> int:
        n = Notification.query.filter_by(user_id=user_id, is_read=True).delete()
        db.session.commit()
        return n
