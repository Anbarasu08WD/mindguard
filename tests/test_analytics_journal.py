"""Tests for the analytics and journal improvements.

Part 1 are pure unit tests (no database needed).
Part 2 are integration tests that need the PostgreSQL test database,
like the rest of the suite.
"""
from datetime import date, datetime, timedelta

from services.analytics_utils import (
    calculate_streaks,
    weekday_averages,
    pearson,
    WEEKDAY_NAMES,
)
from services.journal_utils import (
    word_count,
    reading_minutes,
    sort_entries,
    journal_stats,
    build_markdown_export,
)

TODAY = date(2026, 11, 14)


def _d(n):
    return TODAY - timedelta(days=n)


# ----------------------------- Part 1: unit tests -----------------------------

def test_streak_empty():
    assert calculate_streaks([], TODAY) == (0, 0)


def test_streak_current_and_best():
    assert calculate_streaks([_d(0), _d(1), _d(2), _d(5)], TODAY) == (3, 3)


def test_streak_alive_when_last_checkin_was_yesterday():
    assert calculate_streaks([_d(1), _d(2)], TODAY) == (2, 2)


def test_streak_broken_after_two_missed_days():
    assert calculate_streaks([_d(3), _d(4), _d(5)], TODAY) == (0, 3)


def test_streak_ignores_duplicate_dates():
    assert calculate_streaks([_d(0), _d(0), _d(1)], TODAY) == (2, 2)


def test_weekday_averages():
    monday_a, monday_b = date(2026, 11, 9), date(2026, 11, 16)
    result = weekday_averages([(monday_a, 4), (monday_b, 2)])
    assert result[0] == 3.0
    assert all(v is None for v in result[1:])
    assert len(WEEKDAY_NAMES) == 7


def test_pearson_perfect_and_degenerate():
    assert pearson([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    assert pearson([1, 2, 3, 4], [2, 4, 6, 8]) == 1.0
    assert pearson([1, 1, 1], [1, 2, 3]) is None
    assert pearson([1, 2], [1, 2]) is None


def test_word_count_and_reading_time():
    assert word_count("") == 0
    assert word_count("I'm feeling better today") == 4
    assert reading_minutes(0) == 1
    assert reading_minutes(400) == 2


def _entry(title, days_ago, words):
    return {
        "title": title,
        "content": "word " * words,
        "created_at": datetime(2026, 11, 14) - timedelta(days=days_ago),
        "words": words,
    }


def test_sort_entries_orders():
    items = [_entry("a", 3, 10), _entry("b", 1, 50), _entry("c", 2, 30)]
    assert [e["title"] for e in sort_entries(items, "newest")] == ["b", "c", "a"]
    assert [e["title"] for e in sort_entries(items, "oldest")] == ["a", "c", "b"]
    assert [e["title"] for e in sort_entries(items, "longest")] == ["b", "c", "a"]
    assert [e["title"] for e in sort_entries(items, "bogus")] == ["b", "c", "a"]


def test_journal_stats():
    items = [_entry("a", 3, 10), _entry("b", 1, 50)]
    stats = journal_stats(items)
    assert stats["count"] == 2
    assert stats["total_words"] == 60
    assert stats["avg_words"] == 30
    assert journal_stats([])["last_written"] is None


def test_markdown_export_contains_entries_in_date_order():
    items = [_entry("Later", 0, 3), _entry("Earlier", 5, 3)]
    md = build_markdown_export(items, "Test User")
    assert "# MindGuard journal export" in md
    assert md.index("Earlier") < md.index("Later")
    assert "Entries: 2" in md


# --------------------------- Part 2: integration tests ---------------------------

from models.journal import JournalEntry
from models.mood import MoodRecord
from services.encryption_service import EncryptionService
from services.database_security import set_explicit_rls_user, clear_explicit_rls_user


def _login(client, user, password):
    client.post("/login", data={"email": user.email, "password": password})


def _add_mood(db_session, user, days_ago, mood="Happy", notes="private-note"):
    set_explicit_rls_user(user.user_id)
    db_session.add(MoodRecord(
        user_id=user.user_id, mood=mood, stress_level=4, energy_level=6,
        recorded_at=date.today() - timedelta(days=days_ago), notes=notes,
    ))
    db_session.commit()
    clear_explicit_rls_user()


def test_csv_export_requires_login(client):
    resp = client.get("/analytics/export.csv")
    assert resp.status_code in (301, 302, 401)


def test_csv_export_contains_only_own_rows_and_no_notes(client, user_a, user_b, db_session):
    _add_mood(db_session, user_a, 0, "Happy", notes="user-a-secret-note")
    _add_mood(db_session, user_b, 0, "Very Low", notes="user-b-secret-note")
    _login(client, user_a, "PasswordA_123!")

    resp = client.get("/analytics/export.csv?days=7")
    body = resp.data.decode()

    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert body.splitlines()[0] == "date,mood,mood_score,stress_level,energy_level"
    assert "Happy" in body
    assert "Very Low" not in body            # other user's row is isolated
    assert "secret-note" not in body         # free-text notes are never exported


def test_analytics_page_shows_streak(client, user_a, db_session):
    for n in range(3):
        _add_mood(db_session, user_a, n)
    _login(client, user_a, "PasswordA_123!")
    resp = client.get("/analytics?days=7")
    assert resp.status_code == 200
    assert b"Current streak" in resp.data
    assert b"Mood by day of the week" in resp.data


def test_journal_export_is_own_and_decrypted(client, user_a, user_b, db_session):
    set_explicit_rls_user(user_a.user_id)
    db_session.add(JournalEntry(user_id=user_a.user_id, title="Mine",
                                encrypted_content=EncryptionService.encrypt("my own reflection")))
    db_session.commit()
    set_explicit_rls_user(user_b.user_id)
    db_session.add(JournalEntry(user_id=user_b.user_id, title="Theirs",
                                encrypted_content=EncryptionService.encrypt("someone else's reflection")))
    db_session.commit()
    clear_explicit_rls_user()

    _login(client, user_a, "PasswordA_123!")
    resp = client.get("/journal/export")
    body = resp.data.decode()

    assert resp.status_code == 200
    assert "my own reflection" in body
    assert "someone else's reflection" not in body
    assert "gAAAAA" not in body              # decrypted for the owner, no raw ciphertext


def test_journal_export_blocked_for_admin(client, admin_user):
    _login(client, admin_user, "AdminPass_123!")
    resp = client.get("/journal/export")
    assert resp.status_code in (302, 403)


def test_journal_sort_param_is_accepted_and_sanitised(client, user_a, db_session):
    _login(client, user_a, "PasswordA_123!")
    for order in ("newest", "oldest", "longest", "<script>"):
        resp = client.get(f"/journal?sort={order}")
        assert resp.status_code == 200
