from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, Response
from flask_login import login_required, current_user
from extensions import db
from models.journal import JournalEntry
from services.encryption_service import EncryptionService
from services.security_service import user_required
from services.audit_service import AuditService
from services.journal_utils import word_count, reading_minutes, sort_entries, journal_stats, build_markdown_export

journal_bp = Blueprint("journal", __name__)


@journal_bp.route("/journal")
@login_required
@user_required
def index():
    user_id = current_user.user_id
    search_query = request.args.get("search", "").strip()
    date_filter = request.args.get("date", "").strip()
    sort_order = request.args.get("sort", "newest").strip()
    if sort_order not in ("newest", "oldest", "longest"):
        sort_order = "newest"

    entries = (
        JournalEntry.query.filter_by(user_id=user_id)
        .order_by(JournalEntry.created_at.desc())
        .all()
    )

    decrypted_entries = []
    for e in entries:
        decrypted_text = EncryptionService.decrypt(e.encrypted_content)
        # Apply search filter across title and decrypted content
        if search_query:
            if search_query.lower() not in e.title.lower() and search_query.lower() not in decrypted_text.lower():
                continue
        if date_filter:
            if e.created_at.strftime("%Y-%m-%d") != date_filter:
                continue

        decrypted_entries.append({
            "journal_id": e.journal_id,
            "title": e.title,
            "content": decrypted_text,
            "created_at": e.created_at,
            "updated_at": e.updated_at,
            "words": word_count(decrypted_text),
            "read_min": reading_minutes(word_count(decrypted_text)),
        })

    decrypted_entries = sort_entries(decrypted_entries, sort_order)

    return render_template(
        "journal/index.html",
        entries=decrypted_entries,
        search_query=search_query,
        date_filter=date_filter,
        sort_order=sort_order,
        stats=journal_stats(decrypted_entries),
    )


@journal_bp.route("/journal/export")
@login_required
@user_required
def export():
    """Download the signed-in user's own journal as a Markdown file (decrypted for the owner)."""
    rows = (
        JournalEntry.query.filter_by(user_id=current_user.user_id)
        .order_by(JournalEntry.created_at.asc())
        .all()
    )
    entries = [
        {
            "title": r.title,
            "content": EncryptionService.decrypt(r.encrypted_content),
            "created_at": r.created_at,
        }
        for r in rows
    ]
    AuditService.log_event("JOURNAL_EXPORTED", "SUCCESS", current_user.user_id)
    return Response(
        build_markdown_export(entries, current_user.full_name),
        mimetype="text/markdown",
        headers={"Content-Disposition": "attachment; filename=mindguard_journal.md"},
    )


@journal_bp.route("/journal/add", methods=["GET", "POST"])
@login_required
@user_required
def add():
    user_id = current_user.user_id

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title:
            flash("Journal title is required.", "danger")
            return render_template("journal/form.html", content=content, is_edit=False)

        if not content:
            flash("Reflection content cannot be empty.", "danger")
            return render_template("journal/form.html", title=title, is_edit=False)

        try:
            # Field-level Fernet authenticated encryption
            encrypted_content = EncryptionService.encrypt(content)

            entry = JournalEntry(
                user_id=user_id,
                title=title,
                encrypted_content=encrypted_content,
            )
            db.session.add(entry)
            db.session.commit()

            # Note: We strictly log that a journal entry was created, NEVER the title or content!
            AuditService.log_event("JOURNAL_ENTRY_CREATED", "SUCCESS", user_id)
            flash("Journal entry encrypted and saved securely.", "success")
            return redirect(url_for("journal.index"))
        except Exception as e:
            db.session.rollback()
            flash("Failed to encrypt and store journal reflection. Please try again.", "danger")

    return render_template("journal/form.html", is_edit=False)


@journal_bp.route("/journal/edit/<int:journal_id>", methods=["GET", "POST"])
@login_required
@user_required
def edit(journal_id: int):
    user_id = current_user.user_id
    entry = JournalEntry.query.filter_by(journal_id=journal_id).first()

    if not entry:
        flash("Journal entry not found.", "warning")
        return redirect(url_for("journal.index"))

    # Backend ownership verification
    if entry.user_id != user_id:
        AuditService.log_event("UNAUTHORIZED_JOURNAL_ACCESS_ATTEMPT", "DENIED", user_id)
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title:
            flash("Journal title is required.", "danger")
            return render_template("journal/form.html", entry=entry, content=content, is_edit=True)

        if not content:
            flash("Reflection content cannot be empty.", "danger")
            return render_template("journal/form.html", entry=entry, title=title, is_edit=True)

        try:
            entry.title = title
            entry.encrypted_content = EncryptionService.encrypt(content)
            db.session.commit()

            AuditService.log_event("JOURNAL_ENTRY_UPDATED", "SUCCESS", user_id)
            flash("Journal reflection re-encrypted and updated.", "success")
            return redirect(url_for("journal.index"))
        except Exception:
            db.session.rollback()
            flash("Failed to update journal entry.", "danger")

    # Decrypt for the authorized owner
    decrypted_content = EncryptionService.decrypt(entry.encrypted_content)
    return render_template("journal/form.html", entry=entry, content=decrypted_content, is_edit=True)


@journal_bp.route("/journal/delete/<int:journal_id>", methods=["POST"])
@login_required
@user_required
def delete(journal_id: int):
    user_id = current_user.user_id
    entry = JournalEntry.query.filter_by(journal_id=journal_id).first()

    if not entry:
        flash("Journal entry not found.", "warning")
        return redirect(url_for("journal.index"))

    if entry.user_id != user_id:
        AuditService.log_event("UNAUTHORIZED_JOURNAL_DELETE_ATTEMPT", "DENIED", user_id)
        abort(403)

    try:
        db.session.delete(entry)
        db.session.commit()
        AuditService.log_event("JOURNAL_ENTRY_DELETED", "SUCCESS", user_id)
        flash("Journal entry deleted permanently.", "info")
    except Exception:
        db.session.rollback()
        flash("Could not delete journal entry.", "danger")

    return redirect(url_for("journal.index"))
