from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from extensions import db
from models.mood import MoodRecord
from services.security_service import user_required
from services.audit_service import AuditService
from timeutil import local_today

mood_bp = Blueprint("mood", __name__)

ALLOWED_MOODS = ["Very Happy", "Happy", "Neutral", "Sad", "Very Low"]


@mood_bp.route("/mood")
@login_required
@user_required
def index():
    user_id = current_user.user_id
    search_query = request.args.get("search", "").strip()
    date_filter = request.args.get("date", "").strip()

    query = MoodRecord.query.filter_by(user_id=user_id)

    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            query = query.filter(MoodRecord.recorded_at == filter_date)
        except ValueError:
            pass

    if search_query:
        query = query.filter(
            (MoodRecord.notes.ilike(f"%{search_query}%")) |
            (MoodRecord.mood.ilike(f"%{search_query}%"))
        )

    records = query.order_by(MoodRecord.recorded_at.desc()).all()
    today = local_today()
    today_logged = any(r.recorded_at == today for r in records)

    return render_template(
        "mood/index.html",
        records=records,
        today=today,
        today_logged=today_logged,
        search_query=search_query,
        date_filter=date_filter,
    )


@mood_bp.route("/mood/add", methods=["GET", "POST"])
@login_required
@user_required
def add():
    user_id = current_user.user_id
    today = local_today()

    if request.method == "POST":
        mood = request.form.get("mood", "").strip()
        recorded_at_str = request.form.get("recorded_at", "").strip()
        notes = request.form.get("notes", "").strip()

        try:
            stress_level = int(request.form.get("stress_level", 5))
            energy_level = int(request.form.get("energy_level", 5))
        except (ValueError, TypeError):
            flash("Stress and energy levels must be integer values between 1 and 10.", "danger")
            return render_template("mood/form.html", today=today, is_edit=False)

        # Validation
        if mood not in ALLOWED_MOODS:
            flash(f"Please select a valid mood from: {', '.join(ALLOWED_MOODS)}", "danger")
            return render_template("mood/form.html", today=today, is_edit=False)

        if not (1 <= stress_level <= 10) or not (1 <= energy_level <= 10):
            flash("Stress and energy levels must be between 1 and 10.", "danger")
            return render_template("mood/form.html", today=today, is_edit=False)

        try:
            entry_date = datetime.strptime(recorded_at_str, "%Y-%m-%d").date() if recorded_at_str else today
        except ValueError:
            entry_date = today

        # Check duplicate date policy (one entry per day per user)
        existing = MoodRecord.query.filter_by(user_id=user_id, recorded_at=entry_date).first()
        if existing:
            flash(f"You already have a mood record for {entry_date}. You can edit that record below.", "warning")
            return redirect(url_for("mood.edit", record_id=existing.record_id))

        try:
            record = MoodRecord(
                user_id=user_id,
                mood=mood,
                stress_level=stress_level,
                energy_level=energy_level,
                notes=notes if notes else None,
                recorded_at=entry_date,
            )
            db.session.add(record)
            db.session.commit()
            AuditService.log_event("MOOD_RECORD_CREATED", "SUCCESS", user_id)
            flash("Mood entry saved successfully!", "success")
            return redirect(url_for("mood.index"))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while saving your mood record. Please try again.", "danger")

    return render_template("mood/form.html", today=today, is_edit=False)


@mood_bp.route("/mood/edit/<int:record_id>", methods=["GET", "POST"])
@login_required
@user_required
def edit(record_id: int):
    user_id = current_user.user_id
    record = MoodRecord.query.filter_by(record_id=record_id).first()

    if not record:
        flash("Record not found.", "warning")
        return redirect(url_for("mood.index"))

    # Strict ownership check at application level (backed by PostgreSQL RLS)
    if record.user_id != user_id:
        AuditService.log_event("UNAUTHORIZED_MOOD_EDIT_ATTEMPT", "DENIED", user_id)
        abort(403)

    if request.method == "POST":
        mood = request.form.get("mood", "").strip()
        notes = request.form.get("notes", "").strip()

        try:
            stress_level = int(request.form.get("stress_level", 5))
            energy_level = int(request.form.get("energy_level", 5))
        except (ValueError, TypeError):
            flash("Stress and energy levels must be between 1 and 10.", "danger")
            return render_template("mood/form.html", record=record, is_edit=True)

        if mood not in ALLOWED_MOODS:
            flash("Please choose a valid mood.", "danger")
            return render_template("mood/form.html", record=record, is_edit=True)

        if not (1 <= stress_level <= 10) or not (1 <= energy_level <= 10):
            flash("Stress and energy levels must be between 1 and 10.", "danger")
            return render_template("mood/form.html", record=record, is_edit=True)

        try:
            record.mood = mood
            record.stress_level = stress_level
            record.energy_level = energy_level
            record.notes = notes if notes else None
            db.session.commit()
            AuditService.log_event("MOOD_RECORD_UPDATED", "SUCCESS", user_id)
            flash("Mood entry updated successfully!", "success")
            return redirect(url_for("mood.index"))
        except Exception:
            db.session.rollback()
            flash("Error updating record. Please try again.", "danger")

    return render_template("mood/form.html", record=record, is_edit=True)


@mood_bp.route("/mood/delete/<int:record_id>", methods=["POST"])
@login_required
@user_required
def delete(record_id: int):
    user_id = current_user.user_id
    record = MoodRecord.query.filter_by(record_id=record_id).first()

    if not record:
        flash("Record not found.", "warning")
        return redirect(url_for("mood.index"))

    if record.user_id != user_id:
        AuditService.log_event("UNAUTHORIZED_MOOD_DELETE_ATTEMPT", "DENIED", user_id)
        abort(403)

    try:
        db.session.delete(record)
        db.session.commit()
        AuditService.log_event("MOOD_RECORD_DELETED", "SUCCESS", user_id)
        flash("Mood record deleted successfully.", "info")
    except Exception:
        db.session.rollback()
        flash("Failed to delete record.", "danger")

    return redirect(url_for("mood.index"))
