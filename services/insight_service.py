from datetime import date, timedelta
from typing import Dict, List

from timeutil import local_today
from extensions import db
from models.mood import MoodRecord
from models.report import WellnessReport
from services.analytics_service import MOOD_SCORE_MAP
from services.insight_engine import (
    build_insights, trend_direction, weekly_comparison, weekly_report_text,
)


class InsightService:
    @staticmethod
    def _entries(user_id: int, days: int = 28) -> List[Dict]:
        start = local_today() - timedelta(days=days - 1)
        rows = (
            MoodRecord.query.filter(MoodRecord.user_id == user_id, MoodRecord.recorded_at >= start)
            .order_by(MoodRecord.recorded_at.asc()).all()
        )
        return [
            {
                "date": r.recorded_at,
                "score": MOOD_SCORE_MAP.get(r.mood, 3),
                "stress": r.stress_level,
                "energy": r.energy_level,
            }
            for r in rows
        ]

    @staticmethod
    def overview(user_id: int) -> Dict:
        entries = InsightService._entries(user_id)
        today = local_today()
        direction, slope = trend_direction([e["score"] for e in entries[-14:]])
        return {
            "insights": build_insights(entries, today),
            "trend": direction,
            "slope": slope,
            "comparison": weekly_comparison(entries, today),
            "report_text": weekly_report_text(entries, today),
            "entry_count": len(entries),
        }

    @staticmethod
    def top_insight(user_id: int):
        items = build_insights(InsightService._entries(user_id), local_today())
        return items[0] if items else None

    @staticmethod
    def save_weekly_report(user_id: int) -> WellnessReport:
        """Create or refresh this week's saved report (one per week, keyed by Monday's date)."""
        today = local_today()
        week_start = today - timedelta(days=today.weekday())
        text_ = weekly_report_text(InsightService._entries(user_id), today)
        report = WellnessReport.query.filter_by(user_id=user_id, report_date=week_start).first()
        if report:
            report.report_summary = text_
        else:
            report = WellnessReport(user_id=user_id, report_date=week_start, report_summary=text_)
            db.session.add(report)
        db.session.commit()
        return report

    @staticmethod
    def list_reports(user_id: int, limit: int = 8) -> List[WellnessReport]:
        return (WellnessReport.query.filter_by(user_id=user_id)
                .order_by(WellnessReport.report_date.desc()).limit(limit).all())
