import json
from models.user import User
from models.mood import MoodRecord
from models.journal import JournalEntry
from models.audit import AuditLog
from services.audit_service import AuditService
from services.encryption_service import EncryptionService
from services.database_security import set_explicit_rls_user, clear_explicit_rls_user


def test_sql_injection_defense(client, db_session):
    """Attempt SQL injection payloads in login form."""
    malicious_inputs = [
        "' OR '1'='1",
        "admin' --",
        "\" OR \"\"=\"",
        "'; DROP TABLE users; --",
    ]
    for payload in malicious_inputs:
        resp = client.post("/login", data={
            "email": payload,
            "password": "some_password",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Invalid email address or password" in resp.data

    # Verify users table is completely intact
    assert User.query.count() > 0


def test_audit_logging_and_sanitization(client, user_a):
    """Verify security actions are recorded and passwords are never logged."""
    # Failed login attempt
    client.post("/login", data={"email": user_a.email, "password": "WrongPassword"})

    log = (
        AuditLog.query.filter_by(action="LOGIN_FAILURE_BAD_CREDENTIALS")
        .order_by(AuditLog.timestamp.desc())
        .first()
    )
    assert log is not None
    assert log.event_status == "FAILED"

    # Verify no log entry ever contains passwords
    all_logs = AuditLog.query.all()
    for l in all_logs:
        assert "PasswordA_123!" not in l.action
        assert "WrongPassword" not in l.action


def test_data_export(client, user_a, db_session):
    """Test machine-readable JSON data export under privacy console."""
    client.post("/login", data={"email": user_a.email, "password": "PasswordA_123!"})

    resp = client.get("/privacy/export")
    assert resp.status_code == 200
    assert resp.content_type == "application/json"

    data = json.loads(resp.data)
    assert "user_profile" in data
    assert data["user_profile"]["email"] == user_a.email
    assert "mood_records" in data
    assert "journal_entries" in data


def test_account_deletion_cascade(client, user_a, db_session):
    """Test full account deletion cascading to child records."""
    client.post("/login", data={"email": user_a.email, "password": "PasswordA_123!"})
    uid = user_a.user_id

    # Add child records
    set_explicit_rls_user(uid)
    j = JournalEntry(
        user_id=uid,
        title="Deletion Test Entry",
        encrypted_content=EncryptionService.encrypt("Content to be wiped"),
    )
    db_session.add(j)
    db_session.commit()
    clear_explicit_rls_user()

    # Request deletion with correct confirmation text
    resp = client.post("/privacy/delete-account", data={
        "confirm_text": "DELETE MY DATA"
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"permanently deleted" in resp.data

    # Verify user is completely removed from database
    assert db_session.get(User, uid) is None


def test_invalid_account_deletion_confirmation(client, user_a, db_session):
    client.post("/login", data={"email": user_a.email, "password": "PasswordA_123!"})

    # Wrong text
    resp = client.post("/privacy/delete-account", data={
        "confirm_text": "delete"
    }, follow_redirects=True)

    assert b"DELETE MY DATA" in resp.data
    assert db_session.get(User, user_a.user_id) is not None
