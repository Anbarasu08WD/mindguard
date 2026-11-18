from datetime import date, timedelta
from typing import Dict, Any, List
from sqlalchemy import func
from timeutil import local_today
from extensions import db
from models.mood import MoodRecord

MOOD_SCORE_MAP = {
    "Very Happy": 5,
    "Happy": 4,
    "Neutral": 3,
    "Sad": 2,
    "Very Low": 1,
}

SCORE_TO_MOOD = {v: k for k, v in MOOD_SCORE_MAP.items()}


from services.analytics_utils import (  # noqa: E402
    WEEKDAY_NAMES,
    calculate_streaks,
    weekday_averages,
    pearson,
)

class AnalyticsService:
    @staticmethod
    def get_user_analytics(user_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Calculates personal wellness analytics for the authenticated user
        over a specified number of days (7, 30, 90).
        Uses actual records stored in PostgreSQL.
        """
        end_date = local_today()
        start_date = end_date - timedelta(days=days - 1)

        # Retrieve records in window ordered by date ascending
        records: List[MoodRecord] = (
            MoodRecord.query.filter(
                MoodRecord.user_id == user_id,
                MoodRecord.recorded_at >= start_date,
                MoodRecord.recorded_at <= end_date,
            )
            .order_by(MoodRecord.recorded_at.asc())
            .all()
        )

        # Total entries in window & lifetime
        total_window_entries = len(records)
        lifetime_entries = MoodRecord.query.filter_by(user_id=user_id).count()

        # Build chronological timeline data
        labels = []
        mood_scores = []
        stress_levels = []
        energy_levels = []

        # Count frequencies for pie chart
        mood_counts = {
            "Very Happy": 0,
            "Happy": 0,
            "Neutral": 0,
            "Sad": 0,
            "Very Low": 0,
        }

        total_stress = 0
        total_energy = 0

        for r in records:
            d_str = r.recorded_at.strftime("%b %d")
            labels.append(d_str)
            score = MOOD_SCORE_MAP.get(r.mood, 3)
            mood_scores.append(score)
            stress_levels.append(r.stress_level)
            energy_levels.append(r.energy_level)

            if r.mood in mood_counts:
                mood_counts[r.mood] += 1
            total_stress += r.stress_level
            total_energy += r.energy_level

        avg_stress = round(total_stress / total_window_entries, 1) if total_window_entries > 0 else 0
        avg_energy = round(total_energy / total_window_entries, 1) if total_window_entries > 0 else 0
        avg_mood_score = round(sum(mood_scores) / total_window_entries, 1) if total_window_entries > 0 else 0

        # Comparative analysis (Current period vs Prior period of equal duration)
        prior_start = start_date - timedelta(days=days)
        prior_end = start_date - timedelta(days=1)
        prior_records = (
            MoodRecord.query.filter(
                MoodRecord.user_id == user_id,
                MoodRecord.recorded_at >= prior_start,
                MoodRecord.recorded_at <= prior_end,
            )
            .all()
        )

        prior_count = len(prior_records)
        prior_avg_stress = (
            round(sum(r.stress_level for r in prior_records) / prior_count, 1)
            if prior_count > 0
            else None
        )
        prior_avg_energy = (
            round(sum(r.energy_level for r in prior_records) / prior_count, 1)
            if prior_count > 0
            else None
        )

        # Generate supportive insight text without clinical claims
        insights = []
        if total_window_entries == 0:
            insights.append("No mood entries recorded for this period yet. Add your daily mood to visualize patterns.")
        else:
            if prior_avg_stress is not None:
                if avg_stress < prior_avg_stress:
                    insights.append(
                        f"Your recorded stress levels were lower this period (avg {avg_stress}/10) compared to the previous period (avg {prior_avg_stress}/10)."
                    )
                elif avg_stress > prior_avg_stress:
                    insights.append(
                        f"Your recorded stress levels were higher this period (avg {avg_stress}/10) compared to the previous period (avg {prior_avg_stress}/10). Consider exploring mindful relaxation activities."
                    )
                else:
                    insights.append(f"Your recorded stress levels remained steady at an average of {avg_stress}/10.")

            if prior_avg_energy is not None:
                if avg_energy > prior_avg_energy:
                    insights.append(
                        f"Your energy levels showed an upward trend (avg {avg_energy}/10 vs prior {prior_avg_energy}/10)."
                    )
                elif avg_energy < prior_avg_energy:
                    insights.append(
                        f"Your recorded energy was slightly lower than prior period (avg {avg_energy}/10 vs prior {prior_avg_energy}/10)."
                    )

            # Dominant mood
            if any(mood_counts.values()):
                top_mood = max(mood_counts, key=mood_counts.get)
                if mood_counts[top_mood] > 0:
                    insights.append(f"Your most frequently recorded mood during this timeframe was '{top_mood}'.")


        # ---- Streaks, weekday pattern, consistency, correlation ----
        lifetime_dates = [
            row[0]
            for row in db.session.query(MoodRecord.recorded_at)
            .filter(MoodRecord.user_id == user_id)
            .all()
        ]
        current_streak, best_streak = calculate_streaks(lifetime_dates, end_date)
        weekday_avg = weekday_averages(
            (r.recorded_at, MOOD_SCORE_MAP.get(r.mood, 3)) for r in records
        )
        scored = [(i, v) for i, v in enumerate(weekday_avg) if v is not None]
        best_weekday = WEEKDAY_NAMES[max(scored, key=lambda t: t[1])[0]] if len(scored) >= 2 else None
        hardest_weekday = WEEKDAY_NAMES[min(scored, key=lambda t: t[1])[0]] if len(scored) >= 2 else None
        checkin_rate = round(100 * total_window_entries / days) if days else 0
        mood_stress_corr = pearson(mood_scores, stress_levels) if total_window_entries >= 7 else None

        if current_streak >= 3:
            insights.append(f"You are on a {current_streak}-day check-in streak. Consistency makes your patterns easier to see.")
        if best_weekday and hardest_weekday and best_weekday != hardest_weekday:
            insights.append(f"Your recorded mood tends to be highest on {best_weekday} and lowest on {hardest_weekday} in this period.")
        if mood_stress_corr is not None and abs(mood_stress_corr) >= 0.4:
            direction = "lower" if mood_stress_corr < 0 else "higher"
            insights.append(f"In this period, days with higher stress tended to have {direction} recorded mood (correlation {mood_stress_corr}). This is a pattern in your own entries, not a diagnosis.")

        return {
            "period_days": days,
            "total_entries": total_window_entries,
            "lifetime_entries": lifetime_entries,
            "labels": labels,
            "mood_scores": mood_scores,
            "stress_levels": stress_levels,
            "energy_levels": energy_levels,
            "mood_distribution": mood_counts,
            "avg_stress": avg_stress,
            "avg_energy": avg_energy,
            "avg_mood_score": avg_mood_score,
            "insights": insights,
            "current_streak": current_streak,
            "best_streak": best_streak,
            "weekday_names": WEEKDAY_NAMES,
            "weekday_avg": weekday_avg,
            "best_weekday": best_weekday,
            "hardest_weekday": hardest_weekday,
            "checkin_rate": checkin_rate,
            "mood_stress_corr": mood_stress_corr,
        }
