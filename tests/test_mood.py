from datetime import date
from models.mood import MoodRecord
from services.database_security import set_explicit_rls_user, clear_explicit_rls_user


def test_mood_creation_and_ownership(client, user_a, db_session):
    # Log in as User A
    client.post("/login", data={"email": user_a.email, "password": "PasswordA_123!"})

    today_str = date.today().strftime("%Y-%m-%d")
    resp = client.post("/mood/add", data={
        "mood": "Very Happy",
        "stress_level": "3",
        "energy_level": "8",
        "recorded_at": today_str,
        "notes": "Testing mood checkin flow.",
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Mood entry saved successfully" in resp.data

    set_explicit_rls_user(user_a.user_id)
    rec = MoodRecord.query.filter_by(user_id=user_a.user_id, recorded_at=date.today()).first()
    assert rec is not None
    assert rec.mood == "Very Happy"
    assert rec.stress_level == 3
    assert rec.energy_level == 8
    assert rec.notes == "Testing mood checkin flow."
    clear_explicit_rls_user()


def test_mood_validation_ranges(client, user_a):
    client.post("/login", data={"email": user_a.email, "password": "PasswordA_123!"})

    # Invalid stress level > 10
    resp = client.post("/mood/add", data={
        "mood": "Happy",
        "stress_level": "15",
        "energy_level": "5",
        "recorded_at": date.today().strftime("%Y-%m-%d"),
        "notes": "",
    }, follow_redirects=True)

    assert b"between 1 and 10" in resp.data


def test_mood_edit_and_delete(client, user_a, db_session):
    client.post("/login", data={"email": user_a.email, "password": "PasswordA_123!"})

    set_explicit_rls_user(user_a.user_id)
    rec = MoodRecord(
        user_id=user_a.user_id,
        mood="Neutral",
        stress_level=5,
        energy_level=5,
        recorded_at=date.today(),
        notes="Initial note",
    )
    db_session.add(rec)
    db_session.commit()
    rec_id = rec.record_id

    # Edit
    edit_resp = client.post(f"/mood/edit/{rec_id}", data={
        "mood": "Happy",
        "stress_level": "4",
        "energy_level": "7",
        "notes": "Updated note",
    }, follow_redirects=True)
    assert edit_resp.status_code == 200
    assert b"Mood entry updated successfully" in edit_resp.data

    # Delete
    del_resp = client.post(f"/mood/delete/{rec_id}", follow_redirects=True)
    assert del_resp.status_code == 200
    assert b"deleted successfully" in del_resp.data
    clear_explicit_rls_user()
