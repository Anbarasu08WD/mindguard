"""Tests for the local insight engine (pure) and the insights pages (integration)."""
from datetime import date, timedelta

from services.insight_engine import (
    linear_slope, trend_direction, trailing_run, trailing_rising_steps,
    weekly_comparison, build_insights, weekly_report_text,
)

TODAY = date(2026, 11, 14)


def _entries(scores, stress=None, energy=None):
    n = len(scores)
    stress = stress or [4] * n
    energy = energy or [6] * n
    return [{"date": TODAY - timedelta(days=n - 1 - i), "score": scores[i],
             "stress": stress[i], "energy": energy[i]} for i in range(n)]


def _ids(entries):
    return [i["id"] for i in build_insights(entries, TODAY)]


# ----------------------------- Part 1: pure engine -----------------------------

def test_linear_slope():
    assert linear_slope([1, 2, 3, 4]) == 1.0
    assert linear_slope([3, 3, 3]) == 0.0
    assert linear_slope([5]) is None


def test_trend_direction():
    assert trend_direction([1, 2, 3, 4, 5])[0] == "improving"
    assert trend_direction([5, 4, 3, 2])[0] == "declining"
    assert trend_direction([3, 3, 3, 3])[0] == "steady"
    assert trend_direction([3, 4, 5])[0] == "insufficient"


def test_trailing_helpers():
    assert trailing_run([5, 2, 2, 1], lambda v: v <= 2) == 3
    assert trailing_run([1, 5], lambda v: v <= 2) == 0
    assert trailing_rising_steps([1, 2, 3, 4]) == 3
    assert trailing_rising_steps([4, 3, 2, 3]) == 1


def test_not_enough_data_asks_to_keep_logging():
    assert _ids(_entries([4, 4])) == ["need-data"]
    assert _ids([]) == ["need-data"]


def test_low_mood_run_is_supportive_and_first():
    result = build_insights(_entries([4, 3, 2, 2, 1]), TODAY)
    assert result[0]["id"] == "low-mood-run"
    assert result[0]["tone"] == "support"
    assert "professional" in result[0]["message"]      # points to real-world support
    assert result[0]["evidence"]                        # every insight explains itself


def test_rising_stress_detected():
    assert "stress-rising" in _ids(_entries([3] * 5, stress=[3, 4, 5, 6, 7]))


def test_high_stress_detected_without_rising_run():
    assert "stress-high" in _ids(_entries([3] * 5, stress=[8, 7, 8, 7, 8]))


def test_low_energy_and_good_streak():
    assert "energy-low" in _ids(_entries([3] * 5, energy=[2] * 5))
    assert "mood-good" in _ids(_entries([5, 5, 4, 5, 4, 5, 5]))


def test_every_insight_has_required_fields_and_valid_tone():
    for scores in ([4, 4, 4, 4], [1, 1, 1, 1], [1, 2, 3, 4, 5], [5, 4, 3, 2, 1], [3] * 6):
        for i in build_insights(_entries(scores), TODAY):
            assert {"id", "title", "message", "tone", "evidence"} <= set(i)
            assert i["tone"] in ("positive", "info", "support")


def test_weekly_comparison_and_report_text():
    entries = _entries([4] * 14)
    cmp_ = weekly_comparison(entries, TODAY)
    assert cmp_["this_week"]["count"] == 7 and cmp_["previous_week"]["count"] == 7
    text = weekly_report_text(entries, TODAY)
    assert "7 check-ins" in text and "same as the week before" in text
    assert weekly_report_text([], TODAY) == "No check-ins were recorded in the last 7 days."


def test_report_text_is_aggregate_only():
    text = weekly_report_text(_entries([2, 3, 4, 5, 3, 3, 4]), TODAY).lower()
    for word in ("notes", "journal", "email"):
        assert word not in text


# --------------------------- Part 2: integration tests ---------------------------

from models.mood import MoodRecord
from models.report import WellnessReport
from services.database_security import set_explicit_rls_user, clear_explicit_rls_user


def _login(client, user, password):
    client.post("/login", data={"email": user.email, "password": password})


def _add_mood(db_session, user, days_ago, mood="Happy"):
    set_explicit_rls_user(user.user_id)
    db_session.add(MoodRecord(user_id=user.user_id, mood=mood, stress_level=4, energy_level=6,
                              recorded_at=date.today() - timedelta(days=days_ago), notes="private"))
    db_session.commit()
    clear_explicit_rls_user()


def test_insights_requires_login(client):
    assert client.get("/insights").status_code in (301, 302, 401)


def test_insights_page_loads_with_and_without_data(client, user_a, db_session):
    _login(client, user_a, "PasswordA_123!")
    empty = client.get("/insights")
    assert empty.status_code == 200 and b"Keep logging" in empty.data
    for n in range(5):
        _add_mood(db_session, user_a, n, "Very Low")
    full = client.get("/insights")
    assert full.status_code == 200
    assert b"Why am I seeing this?" in full.data
    assert b"low-mood days in a row" in full.data


def test_weekly_report_is_saved_once_per_week_and_private(client, user_a, user_b, db_session):
    _add_mood(db_session, user_a, 0)
    _login(client, user_a, "PasswordA_123!")
    client.post("/insights/report")
    client.post("/insights/report")                     # second click updates, does not duplicate
    set_explicit_rls_user(user_a.user_id)
    assert WellnessReport.query.filter_by(user_id=user_a.user_id).count() == 1
    clear_explicit_rls_user()
    set_explicit_rls_user(user_b.user_id)
    assert WellnessReport.query.filter_by(user_id=user_a.user_id).count() == 0   # RLS hides it from B
    clear_explicit_rls_user()


def test_insights_blocked_for_admin(client, admin_user):
    _login(client, admin_user, "AdminPass_123!")
    assert client.get("/insights").status_code in (302, 403)


def test_dashboard_shows_local_insight_card(client, user_a, db_session):
    for n in range(4):
        _add_mood(db_session, user_a, n, "Very Low")
    _login(client, user_a, "PasswordA_123!")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Local analysis" in resp.data
