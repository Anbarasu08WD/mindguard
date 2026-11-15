import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app import create_app
from extensions import db
from models.user import User
from models.mood import MoodRecord
from models.journal import JournalEntry
from services.encryption_service import EncryptionService
from services.database_security import set_explicit_rls_user, clear_explicit_rls_user


@pytest.fixture(scope="session")
def app():
    os.environ["FLASK_ENV"] = "testing"
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Disabled for automated client form testing
    return app


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app):
    with app.app_context():
        # Clean test records if any exist with test emails
        test_emails = [
            "test_usera@mindguard.test",
            "test_userb@mindguard.test",
            "test_admin@mindguard.test",
            "new_register@mindguard.test",
        ]
        users = User.query.filter(User.email.in_(test_emails)).all()
        for u in users:
            db.session.delete(u)
        db.session.commit()
        clear_explicit_rls_user()

        yield db.session

        # Cleanup
        try:
            users = User.query.filter(User.email.in_(test_emails)).all()
            for u in users:
                db.session.delete(u)
            db.session.commit()
        except Exception:
            db.session.rollback()
        clear_explicit_rls_user()


@pytest.fixture
def user_a(db_session):
    u = User(
        full_name="Test User A",
        email="test_usera@mindguard.test",
        role="user",
        account_status="active",
    )
    u.set_password("PasswordA_123!")
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def user_b(db_session):
    u = User(
        full_name="Test User B",
        email="test_userb@mindguard.test",
        role="user",
        account_status="active",
    )
    u.set_password("PasswordB_123!")
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def admin_user(db_session):
    u = User(
        full_name="Test Admin",
        email="test_admin@mindguard.test",
        role="admin",
        account_status="active",
    )
    u.set_password("AdminPass_123!")
    db_session.add(u)
    db_session.commit()
    return u
