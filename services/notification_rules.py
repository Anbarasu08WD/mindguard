"""Pure notification rules (no database access), easy to unit test.

Notification text is intentionally generic. It never includes mood notes,
journal text or the user's actual mood values.
"""
import re
from datetime import date, time
from typing import Dict, List, Optional, Set

STREAK_MILESTONES = (3, 7, 14, 30, 60, 100)
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def parse_hhmm(value: str) -> Optional[time]:
    """Parse 'HH:MM' (24h). Returns None for invalid input."""
    m = _TIME_RE.match((value or "").strip())
    if not m:
        return None
    return time(int(m.group(1)), int(m.group(2)))


def safe_internal_link(link: Optional[str]) -> str:
    """Return the link only if it is an internal path; otherwise a safe default."""
    if link and link.startswith("/") and not link.startswith("//") and "\\" not in link:
        return link
    return "/notifications"


def due_notifications(
    *,
    today: date,
    now: time,
    prefs: Dict,
    has_checkin_today: bool,
    current_streak: int,
    entries_last_7_days: int,
    existing_keys: Set[str],
) -> List[Dict]:
    """Decide which notifications should be created right now.

    Every item carries a dedupe_key so calling this repeatedly is idempotent.
    """
    due: List[Dict] = []

    # 1. Daily check-in reminder
    remind_at = parse_hhmm(prefs.get("reminder_time", "20:00")) or time(20, 0)
    key = f"reminder:{today.isoformat()}"
    if prefs.get("daily_reminder", True) and not has_checkin_today and now >= remind_at and key not in existing_keys:
        due.append({
            "dedupe_key": key,
            "category": "reminder",
            "title": "Time for your daily check-in",
            "message": "Take 30 seconds to log how you are feeling today.",
            "link": "/mood/add",
        })

    # 2. Streak milestones
    key = f"streak:{today.isoformat()}:{current_streak}"
    if prefs.get("streak_alerts", True) and current_streak in STREAK_MILESTONES and key not in existing_keys:
        due.append({
            "dedupe_key": key,
            "category": "streak",
            "title": f"{current_streak}-day check-in streak",
            "message": "Nice consistency. Regular check-ins make your patterns easier to see.",
            "link": "/analytics",
        })

    # 3. Weekly summary, offered on Mondays when there is data
    iso = today.isocalendar()
    key = f"weekly:{iso[0]}-W{iso[1]:02d}"
    if prefs.get("weekly_summary", True) and today.weekday() == 0 and entries_last_7_days > 0 and key not in existing_keys:
        due.append({
            "dedupe_key": key,
            "category": "weekly",
            "title": "Your weekly summary is ready",
            "message": f"You logged {entries_last_7_days} check-in{'s' if entries_last_7_days != 1 else ''} in the last 7 days. See your patterns.",
            "link": "/insights",
        })

    return due
