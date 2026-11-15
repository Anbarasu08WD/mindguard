import logging
from flask import request
from extensions import db
from models.audit import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    @staticmethod
    def get_client_ip() -> str:
        if request:
            if request.headers.get("X-Forwarded-For"):
                # Take first IP in comma-separated list
                return request.headers.get("X-Forwarded-For").split(",")[0].strip()
            return request.remote_addr or "127.0.0.1"
        return "127.0.0.1"

    @classmethod
    def log_event(cls, action: str, event_status: str, user_id: int = None) -> None:
        """
        Logs a security or operational event to the database audit_logs table.
        Strictly omits passwords, keys, journal content, or personal notes.
        """
        try:
            ip_addr = cls.get_client_ip()
            log_entry = AuditLog(
                user_id=user_id,
                action=action[:100],
                event_status=event_status[:50],
                ip_address=ip_addr[:45],
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            # Audit failure must not crash application, but should be recorded in server log
            db.session.rollback()
            logger.error(f"Failed to record audit log for action '{action}': {e}")
