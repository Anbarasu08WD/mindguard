from models.user import User
from models.audit import AuditLog


def test_user_registration(client, db_session):
    resp = client.post("/register", data={
        "full_name": "New Registrant",
        "email": "new_register@mindguard.test",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "consent_privacy": "on",
    }, follow_redirects=True)

    assert resp.status_code == 200
    user = User.query.filter_by(email="new_register@mindguard.test").first()
    assert user is not None
    assert user.full_name == "New Registrant"
    assert user.role == "user"
    assert user.account_status == "active"
    assert user.check_password("SecurePassword123!")
    # Password must never be stored in plain text
    assert user.password_hash != "SecurePassword123!"


def test_duplicate_email_prevention(client, user_a):
    resp = client.post("/register", data={
        "full_name": "Imposter User",
        "email": user_a.email,
        "password": "AnotherPassword123!",
        "confirm_password": "AnotherPassword123!",
        "consent_privacy": "on",
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"already exists" in resp.data.lower()


def test_password_strength_validation(client):
    # Weak password without special char or uppercase
    resp = client.post("/register", data={
        "full_name": "Weak Pass User",
        "email": "weak@mindguard.test",
        "password": "password",
        "confirm_password": "password",
        "consent_privacy": "on",
    }, follow_redirects=True)

    assert b"Password must be at least 8 characters" in resp.data or b"uppercase" in resp.data or b"number" in resp.data


def test_login_success_and_logout(client, user_a):
    resp = client.post("/login", data={
        "email": user_a.email,
        "password": "PasswordA_123!",
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Wellness Overview" in resp.data or b"Welcome back" in resp.data

    # Logout
    logout_resp = client.get("/logout", follow_redirects=True)
    assert logout_resp.status_code == 200
    assert b"logged out" in logout_resp.data.lower()


def test_login_invalid_password(client, user_a):
    resp = client.post("/login", data={
        "email": user_a.email,
        "password": "WrongPassword!",
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Invalid email address or password" in resp.data


def test_unauthenticated_dashboard_access(client):
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
