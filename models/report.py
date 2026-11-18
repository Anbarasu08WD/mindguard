from datetime import datetime, date, timezone
from extensions import db
from timeutil import local_today


class WellnessReport(db.Model):
    __tablename__ = "wellness_reports"

    report_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    report_date = db.Column(db.Date, nullable=False, default=local_today)
    report_summary = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<WellnessReport id={self.report_id} user={self.user_id}>"
