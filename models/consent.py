from datetime import datetime, timezone
from extensions import db


class UserConsent(db.Model):
    __tablename__ = "user_consents"

    consent_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = db.Column(db.String(100), nullable=False)  # 'privacy_policy', 'wellness_analytics', 'data_storage'
    consent_status = db.Column(db.String(50), nullable=False, default="GRANTED")  # 'GRANTED', 'REVOKED'
    updated_at = db.Column(
        db.DateTime, 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "consent_type", name="uq_user_consent_type"),
    )

    def __repr__(self) -> str:
        return f"<UserConsent user={self.user_id} type={self.consent_type} status={self.consent_status}>"
