from typing import List, Dict, Any
from datetime import date, timedelta
from extensions import db
from models.suggestion import WellnessSuggestion
from models.mood import MoodRecord
from services.analytics_service import MOOD_SCORE_MAP
from timeutil import local_today


class RecommendationService:
    @staticmethod
    def get_personalized_suggestions(user_id: int) -> Dict[str, Any]:
        """
        Generates supportive rule-based wellness suggestions
        derived from the user's recent recorded patterns.
        """
        # Fetch last 7 days of entries
        seven_days_ago = local_today() - timedelta(days=7)
        recent_records = (
            MoodRecord.query.filter(
                MoodRecord.user_id == user_id,
                MoodRecord.recorded_at >= seven_days_ago,
            )
            .order_by(MoodRecord.recorded_at.desc())
            .all()
        )

        all_suggestions = WellnessSuggestion.query.all()
        categories = sorted(list(set(s.category for s in all_suggestions))) if all_suggestions else []

        recommended: List[WellnessSuggestion] = []
        user_notes = []

        if not recent_records:
            user_notes.append(
                "You haven't recorded a mood entry in the last 7 days. "
                "Checking in regularly can help you recognize personal wellness patterns!"
            )
            # Default to a balanced set of suggestions
            recommended = all_suggestions[:4]
        else:
            avg_stress = sum(r.stress_level for r in recent_records) / len(recent_records)
            avg_energy = sum(r.energy_level for r in recent_records) / len(recent_records)
            avg_score = sum(MOOD_SCORE_MAP.get(r.mood, 3) for r in recent_records) / len(recent_records)

            target_categories = set()

            if avg_stress >= 6.5:
                user_notes.append("Your recent records reflect elevated stress levels. Mindful relaxation and breathing exercises may help you reset.")
                target_categories.add("Relaxation")
                target_categories.add("Mindfulness")

            if avg_energy <= 4.5:
                user_notes.append("Your energy has been on the lower side recently. Small gentle routines and restorative breaks can help recharge your battery.")
                target_categories.add("Healthy Routines")
                target_categories.add("Physical Activity")

            if avg_score <= 2.5:
                user_notes.append("Reflecting on positive moments or writing freely in your encrypted journal can provide clarity during quiet times.")
                target_categories.add("Journaling")
                target_categories.add("Study-Life Balance")

            if not target_categories:
                user_notes.append("Your recorded wellness balance looks steady! Keep up your healthy routines.")
                target_categories.update(["Mindfulness", "Healthy Routines", "Study-Life Balance"])

            # Filter suggestions matching target categories first
            matched = [s for s in all_suggestions if s.category in target_categories]
            others = [s for s in all_suggestions if s.category not in target_categories]
            recommended = (matched + others)[:6]

        return {
            "notes": user_notes,
            "recommended": recommended,
            "all_suggestions": all_suggestions,
            "categories": categories,
        }
