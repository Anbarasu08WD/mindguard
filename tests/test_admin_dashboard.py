"""Tests for admin dashboard improvements: pure helpers + integration."""
from datetime import date, datetime

from services.admin_utils import fill_daily_series, parse_date_param, clamp_page, audit_rows_to_csv


class _Row:
    def __init__(self, log_id, action, status="SUCCESS", user_id=1, ip="127.0.0.1"):
        self.log_id, self.action, self.event_status = log_id, action, status
        self.user_id, self.ip_address = user_id, ip
        self.timestamp = datetime(2026, 11, 14, 10, 30, 0)


# ----------------------------- Part 1: pure helpers -----------------------------

def test_fill_daily_series_zero_fills_and_orders():
    today = date(2026, 11, 14)
    labels, values = fill_daily_series({date(2026, 11, 14): 3, date(2026, 11, 12): 1}, 4, today)
    assert labels == ["Nov 11", "Nov 12", "Nov 13", "Nov 14"]
    assert values == [0, 1, 0, 3]


def test_parse_date_param():
    assert parse_date_param("2026-11-14") == date(2026, 11, 14)
    for bad in ("", "14-11-2026", "2026-13-40", "abc", None):
        assert parse_date_param(bad) is None


def test_clamp_page():
    assert clamp_page(1, 0, 25) == (1, 1)
    assert clamp_page(99, 60, 25) == (3, 3)
    assert clamp_page(-4, 60, 25) == (1, 3)
    assert clamp_page("abc", 60, 25) == (1, 3)
    assert clamp_page(2, 50, 25) == (2, 2)


def test_audit_csv_has_header_and_rows():
    out = audit_rows_to_csv([_Row(1, "USER_LOGIN"), _Row(2, "LOGIN_FAILURE_BAD_CREDENTIALS", "FAILED", None)])
    lines = out.strip().splitlines()
    assert lines[0] == "log_id,timestamp_utc,action,status,user_id,ip_address"
    assert len(lines) == 3
    assert "LOGIN_FAILURE_BAD_CREDENTIALS" in lines[2]


def test_audit_csv_neutralises_formula_injection():
    out = audit_rows_to_csv([_Row(1, "=HYPERLINK(\"http://evil\")", ip="+1.2.3.4")])
    data_line = out.strip().splitlines()[1]
    assert "'=HYPERLINK" in data_line
    assert ",'+1.2.3.4" in data_line


# --------------------------- Part 2: integration tests ---------------------------

def _login(client, user, password):
    client.post("/login", data={"email": user.email, "password": password})


def test_admin_dashboard_shows_live_rls_check_and_charts(client, admin_user):
    _login(client, admin_user, "AdminPass_123!")
    resp = client.get("/admin")
    body = resp.data.decode()
    assert resp.status_code == 200
    assert "Administrative Dashboard" in body
    assert "Tables with FORCE RLS" in body
    assert "signupsChart" in body and "eventsChart" in body


def test_admin_dashboard_forbidden_for_regular_user(client, user_a):
    _login(client, user_a, "PasswordA_123!")
    assert client.get("/admin").status_code in (302, 403)
    assert client.get("/admin/audit-logs/export.csv").status_code in (302, 403)


def test_audit_log_filters_and_pagination_are_safe(client, admin_user):
    _login(client, admin_user, "AdminPass_123!")
    for qs in ("", "?page=999", "?page=-1", "?page=abc", "?from=not-a-date&to=also-bad",
               "?action=LOGIN&status=FAILED&from=2020-01-01&to=2030-01-01"):
        assert client.get("/admin/audit-logs" + qs).status_code == 200


def test_audit_export_is_csv_and_logged(client, admin_user):
    _login(client, admin_user, "AdminPass_123!")
    resp = client.get("/admin/audit-logs/export.csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert resp.data.decode().splitlines()[0] == "log_id,timestamp_utc,action,status,user_id,ip_address"
    assert b"ADMIN_AUDIT_EXPORTED" in client.get("/admin/audit-logs?action=ADMIN_AUDIT").data


def test_admin_pages_contain_no_wellness_content(client, admin_user, user_a, db_session):
    from models.mood import MoodRecord
    from services.database_security import set_explicit_rls_user, clear_explicit_rls_user
    set_explicit_rls_user(user_a.user_id)
    db_session.add(MoodRecord(user_id=user_a.user_id, mood="Very Low", stress_level=9, energy_level=1,
                              recorded_at=date.today(), notes="ultra-secret-admin-must-not-see"))
    db_session.commit()
    clear_explicit_rls_user()
    _login(client, admin_user, "AdminPass_123!")
    for path in ("/admin", "/admin/users", "/admin/audit-logs"):
        assert b"ultra-secret-admin-must-not-see" not in client.get(path).data
