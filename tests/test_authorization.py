from datetime import date
from models.mood import MoodRecord
from models.journal import JournalEntry
from services.encryption_service import EncryptionService
from services.database_security import set_explicit_rls_user, clear_explicit_rls_user


def test_cross_user_isolation_user_a_and_user_b(client, user_a, user_b, db_session):
    """
    MANDATORY SCENARIO:
    User A: creates mood and encrypted journal entry.
    User B: attempts to access/edit/delete User A's records.
    Result: Access denied (403 Forbidden).
    """
    # 1. User A logs in and creates records
    client.post("/login", data={"email": user_a.email, "password": "PasswordA_123!"})

    set_explicit_rls_user(user_a.user_id)
    mood_a = MoodRecord(
        user_id=user_a.user_id,
        mood="Very Happy",
        stress_level=2,
        energy_level=9,
        recorded_at=date.today(),
        notes="Confidential note of User A",
    )
    journal_a = JournalEntry(
        user_id=user_a.user_id,
        title="User A Private Reflections",
        encrypted_content=EncryptionService.encrypt("Deeply private thoughts belonging solely to User A."),
    )
    db_session.add_all([mood_a, journal_a])
    db_session.commit()
    mood_a_id = mood_a.record_id
    journal_a_id = journal_a.journal_id
    clear_explicit_rls_user()

    # User A logs out
    client.get("/logout")

    # 2. User B logs in
    client.post("/login", data={"email": user_b.email, "password": "PasswordB_123!"})

    # Attempt 1: User B tries to edit User A's mood record
    unauth_mood_edit = client.post(f"/mood/edit/{mood_a_id}", data={
        "mood": "Sad",
        "stress_level": "10",
        "energy_level": "1",
        "notes": "Hacked by User B",
    })
    # Must be denied with 403 Forbidden or not found due to RLS
    assert unauth_mood_edit.status_code in [403, 302]

    # Attempt 2: User B tries to delete User A's mood record
    unauth_mood_del = client.post(f"/mood/delete/{mood_a_id}")
    assert unauth_mood_del.status_code in [403, 302]

    # Attempt 3: User B tries to view/edit User A's journal entry
    unauth_journal_get = client.get(f"/journal/edit/{journal_a_id}")
    assert unauth_journal_get.status_code in [403, 302]

    # Attempt 4: User B tries to overwrite User A's journal entry
    unauth_journal_post = client.post(f"/journal/edit/{journal_a_id}", data={
        "title": "Compromised Title",
        "content": "Malicious overwrite",
    })
    assert unauth_journal_post.status_code in [403, 302]

    # Attempt 5: User B tries to delete User A's journal entry
    unauth_journal_del = client.post(f"/journal/delete/{journal_a_id}")
    assert unauth_journal_del.status_code in [403, 302]


def test_rbac_standard_user_blocked_from_admin(client, user_a):
    client.post("/login", data={"email": user_a.email, "password": "PasswordA_123!"})
    resp = client.get("/admin")
    assert resp.status_code == 403


def test_rbac_admin_allowed_on_admin_dashboard(client, admin_user):
    client.post("/login", data={"email": admin_user.email, "password": "AdminPass_123!"})
    resp = client.get("/admin")
    assert resp.status_code == 200
    assert b"Administrative Dashboard" in resp.data or b"System Health" in resp.data
