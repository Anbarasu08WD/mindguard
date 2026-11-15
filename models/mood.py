from datetime import datetime, date, timezone
from extensions import db


class MoodRecord(db.Model):
    __tablename__ = "mood_records"

    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    mood = db.Column(db.String(30), nullable=False)  # 'Very Happy', 'Happy', 'Neutral', 'Sad', 'Very Low'
    stress_level = db.Column(db.Integer, nullable=False)  # 1 to 10
    energy_level = db.Column(db.Integer, nullable=False)  # 1 to 10
    notes = db.Column(db.Text, nullable=True)
    recorded_at = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.CheckConstraint("stress_level >= 1 AND stress_level <= 10", name="chk_mood_stress_range"),
        db.CheckConstraint("energy_level >= 1 AND energy_level <= 10", name="chk_mood_energy_range"),
        db.UniqueConstraint("user_id", "recorded_at", name="uq_user_recorded_date"),
    )

    def __repr__(self) -> str:
        return f"<MoodRecord user={self.user_id} date={self.recorded_at} mood={self.mood}>"
