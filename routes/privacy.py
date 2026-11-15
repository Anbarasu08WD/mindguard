import json
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, abort
from flask_login import login_required, logout_user, current_user
from extensions import db
from models.user import User
from models.mood import MoodRecord
from models.journal import JournalEntry
from models.consent import UserConsent
from models.session import UserSession
from services.encryption_service import EncryptionService
from services.security_service import user_required
from services.audit_service import AuditService

privacy_bp = Blueprint("privacy", __name__)


@privacy_bp.route("/privacy")
@login_required
@user_required
def index():
    user_id = current_user.user_id

    # Gather privacy metrics
    mood_count = MoodRecord.query.filter_by(user_id=user_id).count()
    journal_count = JournalEntry.query.filter_by(user_id=user_id).count()
    consents = UserConsent.query.filter_by(user_id=user_id).all()
    sessions = UserSession.query.filter_by(user_id=user_id).order_by(UserSession.created_at.desc()).limit(5).all()

    return render_template(
        "privacy/index.html",
        mood_count=mood_count,
        journal_count=journal_count,
        consents=consents,
        sessions=sessions,
    )


@privacy_bp.route("/privacy/consent", methods=["POST"])
@login_required
@user_required
def update_consent():
    user_id = current_user.user_id
    analytics_consent = "analytics_consent" in request.form
    storage_consent = "storage_consent" in request.form

    try:
        # Update or create analytics consent
        c_analytics = UserConsent.query.filter_by(user_id=user_id, consent_type="wellness_analytics").first()
        if not c_analytics:
            c_analytics = UserConsent(user_id=user_id, consent_type="wellness_analytics")
            db.session.add(c_analytics)
        c_analytics.consent_status = "GRANTED" if analytics_consent else "REVOKED"

        # Update or create storage consent
        c_storage = UserConsent.query.filter_by(user_id=user_id, consent_type="data_storage").first()
        if not c_storage:
            c_storage = UserConsent(user_id=user_id, consent_type="data_storage")
            db.session.add(c_storage)
        c_storage.consent_status = "GRANTED" if storage_consent else "REVOKED"

        db.session.commit()
        AuditService.log_event("PRIVACY_CONSENT_UPDATED", "SUCCESS", user_id)
        flash("Privacy preferences updated successfully.", "success")
    except Exception:
        db.session.rollback()
        flash("Could not update privacy preferences.", "danger")

    return redirect(url_for("privacy.index"))


@privacy_bp.route("/privacy/export")
@login_required
@user_required
def export_data():
    """Generates complete GDPR/Privacy-compliant machine-readable JSON data export."""
    user_id = current_user.user_id

    # 1. Profile information
    user = db.session.get(User, user_id)
    profile_data = {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "account_status": user.account_status,
        "created_at": user.created_at.isoformat(),
    }

    # 2. Mood records
    moods = MoodRecord.query.filter_by(user_id=user_id).order_by(MoodRecord.recorded_at.asc()).all()
    mood_list = [
        {
            "record_id": m.record_id,
            "recorded_at": m.recorded_at.isoformat(),
            "mood": m.mood,
            "stress_level": m.stress_level,
            "energy_level": m.energy_level,
            "notes": m.notes,
        }
        for m in moods
    ]

    # 3. Journal entries (decrypted for owner)
    journals = JournalEntry.query.filter_by(user_id=user_id).order_by(JournalEntry.created_at.asc()).all()
    journal_list = [
        {
            "journal_id": j.journal_id,
            "title": j.title,
            "content": EncryptionService.decrypt(j.encrypted_content),
            "created_at": j.created_at.isoformat(),
            "updated_at": j.updated_at.isoformat(),
        }
        for j in journals
    ]

    # 4. Consent records
    consents = UserConsent.query.filter_by(user_id=user_id).all()
    consent_list = [
        {
            "consent_type": c.consent_type,
            "consent_status": c.consent_status,
            "updated_at": c.updated_at.isoformat(),
        }
        for c in consents
    ]

    export_payload = {
        "mindguard_export_metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "description": "MindGuard Privacy-Preserving Personal Wellness Data Export",
            "compliance": "Privacy and User Data Portability Compliant",
        },
        "user_profile": profile_data,
        "mood_records": mood_list,
        "journal_entries": journal_list,
        "consents": consent_list,
    }

    AuditService.log_event("USER_DATA_EXPORTED", "SUCCESS", user_id)

    json_str = json.dumps(export_payload, indent=2)
    filename = f"mindguard_data_export_user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return Response(
        json_str,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@privacy_bp.route("/privacy/delete-account", methods=["POST"])
@login_required
@user_required
def delete_account():
    """Permanently deletes user account and all cascaded data."""
    user_id = current_user.user_id
    confirm_text = request.form.get("confirm_text", "").strip()

    if confirm_text != "DELETE MY DATA":
        flash("Confirmation text must match 'DELETE MY DATA' exactly to proceed.", "danger")
        return redirect(url_for("privacy.index"))

    try:
        user = db.session.get(User, user_id)
        AuditService.log_event("USER_ACCOUNT_DELETION", "SUCCESS", user_id)

        logout_user()
        db.session.delete(user)
        db.session.commit()

        flash("Your account and all associated wellness records have been permanently deleted.", "info")
        return redirect(url_for("landing"))
    except Exception as e:
        db.session.rollback()
        flash("Failed to delete account. Please try again or contact support.", "danger")
        return redirect(url_for("privacy.index"))
