from models.journal import JournalEntry
from services.encryption_service import EncryptionService
from services.database_security import set_explicit_rls_user, clear_explicit_rls_user


def test_journal_encryption_and_decryption(client, user_a, db_session):
    client.post("/login", data={"email": user_a.email, "password": "PasswordA_123!"})

    raw_text = "This is a confidential personal reflection that must never be in plaintext in the database."
    resp = client.post("/journal/add", data={
        "title": "Secret Thoughts",
        "content": raw_text,
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"encrypted and saved securely" in resp.data

    set_explicit_rls_user(user_a.user_id)
    entry = JournalEntry.query.filter_by(user_id=user_a.user_id, title="Secret Thoughts").first()
    assert entry is not None
    # 1. Stored content in database must NOT equal raw_text
    assert entry.encrypted_content != raw_text
    # 2. Must start with Fernet token prefix (gAAAAA)
    assert entry.encrypted_content.startswith("gAAAAA")
    # 3. Decryption service must restore the original text
    decrypted = EncryptionService.decrypt(entry.encrypted_content)
    assert decrypted == raw_text
    clear_explicit_rls_user()


def test_journal_edit_and_delete(client, user_a, db_session):
    client.post("/login", data={"email": user_a.email, "password": "PasswordA_123!"})

    set_explicit_rls_user(user_a.user_id)
    entry = JournalEntry(
        user_id=user_a.user_id,
        title="Editable Journal",
        encrypted_content=EncryptionService.encrypt("Original reflection content."),
    )
    db_session.add(entry)
    db_session.commit()
    jid = entry.journal_id

    # Edit
    edit_resp = client.post(f"/journal/edit/{jid}", data={
        "title": "Updated Title",
        "content": "New reflection content.",
    }, follow_redirects=True)
    assert edit_resp.status_code == 200
    assert b"re-encrypted and updated" in edit_resp.data

    # Verify new content is encrypted
    refreshed = db_session.get(JournalEntry, jid)
    assert EncryptionService.decrypt(refreshed.encrypted_content) == "New reflection content."

    # Delete
    del_resp = client.post(f"/journal/delete/{jid}", follow_redirects=True)
    assert del_resp.status_code == 200
    assert b"deleted permanently" in del_resp.data
    clear_explicit_rls_user()
