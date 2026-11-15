from datetime import datetime, timezone
from extensions import db


class WellnessSuggestion(db.Model):
    __tablename__ = "wellness_suggestions"

    suggestion_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Mindfulness, Relaxation, Healthy Routines, etc.
    description = db.Column(db.Text, nullable=False)
    estimated_minutes = db.Column(db.Integer, nullable=False, default=10)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<WellnessSuggestion {self.title} ({self.category})>"
