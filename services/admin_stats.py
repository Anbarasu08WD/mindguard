from datetime import date, datetime, timedelta, timezone
from typing import Dict, List

from sqlalchemy import func, or_, text

from extensions import db
from models.audit import AuditLog
from models.user import User
from services.admin_utils import fill_daily_series

SECURITY_EVENT_FILTER = or_(
    AuditLog.action.like("LOGIN_FAILURE%"),
    AuditLog.action.like("LOGIN_ATTEMPT%"),
    AuditLog.action.like("UNAUTHORIZED%"),
    AuditLog.event_status.in_(["FAILED", "DENIED"]),
)


class AdminStatsService:
    """Aggregate-only statistics. Admins never see mood or journal records."""

    @staticmethod
    def signups_by_day(days: int = 14):
        start = datetime.now(timezone.utc) - timedelta(days=days)
        rows = (
            db.session.query(func.date(User.created_at), func.count(User.user_id))
            .filter(User.created_at >= start)
            .group_by(func.date(User.created_at)).all()
        )
        return fill_daily_series({d: c for d, c in rows}, days, date.today())

    @staticmethod
    def security_events_by_day(days: int = 14):
        start = datetime.now(timezone.utc) - timedelta(days=days)
        rows = (
            db.session.query(func.date(AuditLog.timestamp), func.count(AuditLog.log_id))
            .filter(AuditLog.timestamp >= start, SECURITY_EVENT_FILTER)
            .group_by(func.date(AuditLog.timestamp)).all()
        )
        return fill_daily_series({d: c for d, c in rows}, days, date.today())

    @staticmethod
    def top_actions(days: int = 30, limit: int = 8) -> List[Dict]:
        start = datetime.now(timezone.utc) - timedelta(days=days)
        rows = (
            db.session.query(AuditLog.action, func.count(AuditLog.log_id).label("n"))
            .filter(AuditLog.timestamp >= start)
            .group_by(AuditLog.action).order_by(func.count(AuditLog.log_id).desc())
            .limit(limit).all()
        )
        return [{"action": a, "count": n} for a, n in rows]

    @staticmethod
    def user_summary() -> Dict:
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        return {
            "total": User.query.count(),
            "active": User.query.filter_by(account_status="active").count(),
            "disabled": User.query.filter_by(account_status="disabled").count(),
            "admins": User.query.filter_by(role="admin").count(),
            "new_7d": User.query.filter(User.created_at >= week_ago).count(),
        }

    @staticmethod
    def failed_login_count() -> int:
        return AuditLog.query.filter(
            or_(AuditLog.action.like("LOGIN_FAILURE%"), AuditLog.action.like("LOGIN_ATTEMPT%"))
        ).count()

    @staticmethod
    def rls_health() -> Dict:
        """Live verification of the database security posture, read from PostgreSQL catalogs."""
        result = {"ok": False, "role": None, "superuser": None, "bypass_rls": None,
                  "tables_total": 0, "tables_forced": 0, "unprotected": []}
        try:
            role = db.session.execute(text(
                "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
            )).one()
            result.update(role=role[0], superuser=bool(role[1]), bypass_rls=bool(role[2]))

            rows = db.session.execute(text("""
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname <> 'alembic_version'
                ORDER BY c.relname
            """)).all()
            # wellness_suggestions is a shared read-only catalogue but is still RLS-forced by init_db
            result["tables_total"] = len(rows)
            result["tables_forced"] = sum(1 for r in rows if r[1] and r[2])
            result["unprotected"] = [r[0] for r in rows if not (r[1] and r[2])]
            result["ok"] = (not result["superuser"] and not result["bypass_rls"]
                            and result["tables_total"] > 0 and not result["unprotected"])
        except Exception:
            db.session.rollback()
        return result
