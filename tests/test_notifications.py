"""Tests for notifications: pure rules (no DB) and integration (PostgreSQL + RLS)."""
from datetime import date, time

from services.notification_rules import (
    parse_hhmm, safe_internal_link, due_notifications, STREAK_MILESTONES,
)

PREFS = {"daily_reminder": True, "reminder_time": "20:00", "streak_alerts": True, "weekly_summary": True}


def _due(**over):
    args = dict(
        today=date(2026, 11, 11),  # a Wednesday
        now=time(21, 0), prefs=dict(PREFS), has_checkin_today=False,
        current_streak=0, entries_last_7_days=0, existing_keys=set(),
    )
    args.update(over)
    return due_notifications(**args)


# ----------------------------- Part 1: pure rules -----------------------------

def test_parse_hhmm_valid_and_invalid():
    assert parse_hhmm("20:00") == time(20, 0)
    assert parse_hhmm("00:05") == time(0, 5)
    for bad in ("", "24:00", "9:00", "12:60", "abc", None, "20:00:00"):
        assert parse_hhmm(bad) is None


def test_safe_internal_link_blocks_open_redirects():
    assert safe_internal_link("/mood/add") == "/mood/add"
    for evil in ("https://evil.example", "//evil.example", "javascript:alert(1)", "/\\evil.example", "", None):
        assert safe_internal_link(evil) == "/notifications"


def test_reminder_due_after_time_when_not_checked_in():
    items = _due()
    assert [i["category"] for i in items] == ["reminder"]
    assert items[0]["dedupe_key"] == "reminder:2026-11-11"


def test_reminder_not_due_before_time_or_if_already_checked_in():
    assert _due(now=time(19, 59)) == []
    assert _due(has_checkin_today=True) == []


def test_reminder_respects_preference_and_dedupe():
    assert _due(prefs={**PREFS, "daily_reminder": False}) == []
    assert _due(existing_keys={"reminder:2026-11-11"}) == []


def test_streak_notification_only_on_milestones():
    for n in STREAK_MILESTONES:
        cats = [i["category"] for i in _due(current_streak=n, has_checkin_today=True)]
        assert cats == ["streak"]
    assert _due(current_streak=4, has_checkin_today=True) == []
    assert _due(current_streak=7, has_checkin_today=True, prefs={**PREFS, "streak_alerts": False}) == []


def test_weekly_summary_only_on_monday_with_data():
    monday = date(2026, 11, 9)
    items = _due(today=monday, has_checkin_today=True, entries_last_7_days=5)
    assert [i["category"] for i in items] == ["weekly"]
    assert "5 check-ins" in items[0]["message"]
    assert _due(today=monday, has_checkin_today=True, entries_last_7_days=0) == []
    assert _due(has_checkin_today=True, entries_last_7_days=5) == []   # Wednesday


def test_notification_text_never_contains_wellness_content():
    items = _due(today=date(2026, 11, 9), current_streak=7, entries_last_7_days=3)
    blob = " ".join(i["title"] + " " + i["message"] for i in items).lower()
    for word in ("journal entry", "very low", "sad", "notes:"):
        assert word not in blob


# --------------------------- Part 2: integration tests ---------------------------

import pytest
from sqlalchemy import text, create_engine
from config import Config
from models.notification import Notification, NotificationPreference
from services.notification_service import NotificationService
from services.database_security import set_explicit_rls_user, clear_explicit_rls_user


def _login(client, user, password):
    client.post("/login", data={"email": user.email, "password": password})


def _make(db_session, user, title="Hello", category="insight", read=False, link="/dashboard", key=None):
    set_explicit_rls_user(user.user_id)
    n = Notification(user_id=user.user_id, category=category, title=title, message="msg",
                     link=link, is_read=read, dedupe_key=key)
    db_session.add(n)
    db_session.commit()
    nid = n.notification_id
    clear_explicit_rls_user()
    return nid


def test_notifications_page_requires_login(client):
    assert client.get("/notifications").status_code in (301, 302, 401)


def test_notifications_page_lists_own_only(client, user_a, user_b, db_session):
    _make(db_session, user_a, "Only for A")
    _make(db_session, user_b, "Only for B")
    _login(client, user_a, "PasswordA_123!")
    body = client.get("/notifications").data.decode()
    assert "Only for A" in body
    assert "Only for B" not in body


def test_open_marks_read_and_redirects_internal(client, user_a, db_session):
    nid = _make(db_session, user_a, link="/analytics")
    _login(client, user_a, "PasswordA_123!")
    resp = client.post(f"/notifications/{nid}/open")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/analytics")
    set_explicit_rls_user(user_a.user_id)
    assert db_session.get(Notification, nid).is_read is True
    clear_explicit_rls_user()


def test_open_with_unsafe_stored_link_falls_back(client, user_a, db_session):
    nid = _make(db_session, user_a, link="https://evil.example")
    _login(client, user_a, "PasswordA_123!")
    resp = client.post(f"/notifications/{nid}/open")
    assert resp.status_code == 302
    assert "evil.example" not in resp.headers["Location"]


def test_user_cannot_open_another_users_notification(client, user_a, user_b, db_session):
    nid = _make(db_session, user_b, "B private")
    _login(client, user_a, "PasswordA_123!")
    resp = client.post(f"/notifications/{nid}/open", follow_redirects=True)
    assert b"Notification not found" in resp.data
    set_explicit_rls_user(user_b.user_id)
    assert db_session.get(Notification, nid).is_read is False   # B's notification untouched
    clear_explicit_rls_user()


def test_read_all_and_clear_read(client, user_a, db_session):
    _make(db_session, user_a, "one")
    _make(db_session, user_a, "two", read=True)
    _login(client, user_a, "PasswordA_123!")
    client.post("/notifications/read-all")
    client.post("/notifications/clear")
    set_explicit_rls_user(user_a.user_id)
    assert Notification.query.filter_by(user_id=user_a.user_id, category="insight").count() == 0
    clear_explicit_rls_user()


def test_settings_save_and_validate(client, user_a, db_session):
    _login(client, user_a, "PasswordA_123!")
    ok = client.post("/notifications/settings", data={"reminder_time": "07:30", "daily_reminder": "on"},
                     follow_redirects=True)
    assert b"preferences saved" in ok.data
    set_explicit_rls_user(user_a.user_id)
    pref = NotificationPreference.query.filter_by(user_id=user_a.user_id).first()
    assert pref.reminder_time == "07:30"
    assert pref.daily_reminder is True and pref.weekly_summary is False   # unchecked boxes become False
    clear_explicit_rls_user()

    bad = client.post("/notifications/settings", data={"reminder_time": "99:99"}, follow_redirects=True)
    assert b"valid reminder time" in bad.data


def test_create_is_idempotent_with_dedupe_key(user_a, db_session):
    set_explicit_rls_user(user_a.user_id)
    assert NotificationService.create(user_a.user_id, "reminder", "t", "m", "/mood/add", "k1") is True
    assert NotificationService.create(user_a.user_id, "reminder", "t", "m", "/mood/add", "k1") is False
    assert Notification.query.filter_by(user_id=user_a.user_id, dedupe_key="k1").count() == 1
    clear_explicit_rls_user()


def test_notifications_blocked_for_admin(client, admin_user):
    _login(client, admin_user, "AdminPass_123!")
    assert client.get("/notifications").status_code in (302, 403)


def test_rls_isolates_notifications_table_directly(user_a, user_b, db_session):
    """Database-level proof: the restricted role cannot see or forge another user's notification."""
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(user_a.user_id)})
            conn.execute(text("INSERT INTO notifications (user_id, category, title, message, is_read, created_at) "
                              "VALUES (:u, 'insight', 'a-only', 'm', false, CURRENT_TIMESTAMP)"), {"u": user_a.user_id})
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(user_b.user_id)})
            assert conn.execute(text("SELECT count(*) FROM notifications")).scalar() == 0
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(user_a.user_id)})
            with pytest.raises(Exception) as exc:
                conn.execute(text("INSERT INTO notifications (user_id, category, title, message, is_read, created_at) "
                                  "VALUES (:other, 'insight', 'forged', 'm', false, CURRENT_TIMESTAMP)"),
                             {"other": user_b.user_id})
            assert "row-level security" in str(exc.value).lower()
