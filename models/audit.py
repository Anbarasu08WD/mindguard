from datetime import datetime, timezone
from extensions import db

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    __table_args__ = {
        "implicit_returning": False
    }

    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)
    event_status = db.Column(db.String(50), nullable=False)  # 'SUCCESS', 'FAILED', 'DENIED'
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    ip_address = db.Column(db.String(45), nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog action={self.action} status={self.event_status} user={self.user_id}>"
