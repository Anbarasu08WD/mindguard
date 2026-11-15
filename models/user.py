from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # 'user', 'admin'
    account_status = db.Column(db.String(20), nullable=False, default="active")  # 'active', 'disabled'
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    mood_records = db.relationship("MoodRecord", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    journal_entries = db.relationship("JournalEntry", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    wellness_reports = db.relationship("WellnessReport", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    consents = db.relationship("UserConsent", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    sessions = db.relationship("UserSession", backref="user", cascade="all, delete-orphan", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_id(self) -> str:
        return str(self.user_id)

    @property
    def is_active(self) -> bool:
        return self.account_status == "active"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
