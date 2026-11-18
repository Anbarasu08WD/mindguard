"""Timezone-aware 'today' and 'now' helpers.

Vercel runs on UTC. Set the APP_TIMEZONE environment variable (for example
Asia/Kolkata) so check-ins, streaks and reminders follow your users' local day.
If APP_TIMEZONE is not set, the server's own clock is used (local development).
This module has no Flask or database imports, so it is safe to import anywhere.
"""
import os
from datetime import date, datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


def _tz():
    name = os.getenv("APP_TIMEZONE", "").strip()
    if not name or ZoneInfo is None:
        return None
    try:
        return ZoneInfo(name)
    except Exception:
        return None


def local_now() -> datetime:
    """Current wall-clock time (naive) in APP_TIMEZONE, or the server clock if unset."""
    tz = _tz()
    return datetime.now(tz).replace(tzinfo=None) if tz else datetime.now()


def local_today() -> date:
    return local_now().date()
