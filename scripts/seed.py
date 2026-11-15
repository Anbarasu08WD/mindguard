import os
import sys
from datetime import date, timedelta, datetime, timezone

# Add parent directory to sys.path so scripts can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from extensions import db
from models.user import User
from models.mood import MoodRecord
from models.journal import JournalEntry
from models.suggestion import WellnessSuggestion
from models.consent import UserConsent
from services.encryption_service import EncryptionService
from services.database_security import set_explicit_rls_user, clear_explicit_rls_user
from database import init_db


def seed():
    app = create_app("development")
    with app.app_context():
        print("[*] Initializing database schema and RLS policies...")
        init_db(app)

        print("[*] Checking existing seed data...")
        admin_user = User.query.filter_by(email="admin@mindguard.local").first()
        if not admin_user:
            admin_user = User(
                full_name="Security Administrator",
                email="admin@mindguard.local",
                role="admin",
                account_status="active",
            )
            admin_user.set_password("AdminPassword2026!")
            db.session.add(admin_user)

        user_a = User.query.filter_by(email="alex@mindguard.local").first()
        if not user_a:
            user_a = User(
                full_name="Alex Rivera",
                email="alex@mindguard.local",
                role="user",
                account_status="active",
            )
            user_a.set_password("UserA_Password2026!")
            db.session.add(user_a)

        user_b = User.query.filter_by(email="sam@mindguard.local").first()
        if not user_b:
            user_b = User(
                full_name="Sam Taylor",
                email="sam@mindguard.local",
                role="user",
                account_status="active",
            )
            user_b.set_password("UserB_Password2026!")
            db.session.add(user_b)

        db.session.commit()
        print(f"[+] Created Users: Admin (ID {admin_user.user_id}), User A (ID {user_a.user_id}), User B (ID {user_b.user_id})")

        # Consents
        for u in [user_a, user_b]:
            db.session.add(UserConsent(user_id=u.user_id, consent_type="privacy_policy", consent_status="GRANTED"))
            db.session.add(UserConsent(user_id=u.user_id, consent_type="wellness_analytics", consent_status="GRANTED"))
            db.session.add(UserConsent(user_id=u.user_id, consent_type="data_storage", consent_status="GRANTED"))
        db.session.commit()

        # Seed Standard Suggestions
        if WellnessSuggestion.query.count() == 0:
            print("[*] Seeding curated wellness suggestions...")
            suggestions = [
                WellnessSuggestion(
                    title="Mindful Box Breathing",
                    category="Mindfulness",
                    description="Inhale for 4 seconds, hold for 4 seconds, exhale for 4 seconds, and hold for 4 seconds. Repeat for 4 full cycles to settle the nervous system.",
                    estimated_minutes=5,
                ),
                WellnessSuggestion(
                    title="Progressive Muscle Relaxation",
                    category="Relaxation",
                    description="Tense and consciously release muscle groups starting from your toes up to your neck. Helps release physical tension stored throughout the body.",
                    estimated_minutes=10,
                ),
                WellnessSuggestion(
                    title="Screen-Free Evening Wind-Down",
                    category="Healthy Routines",
                    description="Power down all digital screens 30 minutes before resting. Engage in gentle reading or calming tea to promote deeper restorative rest.",
                    estimated_minutes=30,
                ),
                WellnessSuggestion(
                    title="Three Positive Moments Reflection",
                    category="Journaling",
                    description="Note down three specific moments today that felt grounding, enjoyable, or meaningful, regardless of how modest they were.",
                    estimated_minutes=8,
                ),
                WellnessSuggestion(
                    title="Gentle Nature Stroll",
                    category="Physical Activity",
                    description="Step outside for a brisk 15-minute walk without headphones. Observe the surroundings and let your gaze shift to distant natural sights.",
                    estimated_minutes=15,
                ),
                WellnessSuggestion(
                    title="Pomodoro Study-Life Pacing",
                    category="Study-Life Balance",
                    description="Structure study blocks into 25 minutes of deep focus followed by 5 minutes of standing up, hydrating, and stretching.",
                    estimated_minutes=25,
                ),
                WellnessSuggestion(
                    title="Sensory 5-4-3-2-1 Grounding",
                    category="Mindfulness",
                    description="Name 5 things you can see, 4 you can feel, 3 you can hear, 2 you can smell, and 1 you can taste to bring yourself into the present moment.",
                    estimated_minutes=6,
                ),
                WellnessSuggestion(
                    title="Desk Posture Reset",
                    category="Relaxation",
                    description="Roll your shoulders back, loosen your jaw, and stretch your spine vertically to eliminate accumulated desk fatigue.",
                    estimated_minutes=4,
                ),
            ]
            db.session.add_all(suggestions)
            db.session.commit()

        # Seed User A Mood & Encrypted Journal records (Setting RLS context for User A)
        set_explicit_rls_user(user_a.user_id)
        if MoodRecord.query.filter_by(user_id=user_a.user_id).count() == 0:
            print("[*] Seeding records for User A...")
            today = date.today()

        user_a_moods = [
            {"offset": 10, "mood": "Happy", "stress": 4, "energy": 7, "notes": "Had a productive study session with classmates."},
            {"offset": 9, "mood": "Very Happy", "stress": 3, "energy": 8, "notes": "Completed the database project milestone ahead of schedule."},
            {"offset": 8, "mood": "Neutral", "stress": 5, "energy": 6, "notes": "Regular quiet day at the library."},
            {"offset": 7, "mood": "Sad", "stress": 7, "energy": 4, "notes": "Felt overwhelmed with upcoming exam deadlines."},
            {"offset": 6, "mood": "Very Low", "stress": 8, "energy": 3, "notes": "Struggled with sleep; felt drained during morning lectures."},
            {"offset": 5, "mood": "Neutral", "stress": 6, "energy": 5, "notes": "Took a relaxing break in the afternoon to recharge."},
            {"offset": 4, "mood": "Happy", "stress": 4, "energy": 7, "notes": "Went for an evening walk; mood rebounded positively."},
            {"offset": 3, "mood": "Happy", "stress": 4, "energy": 8, "notes": "Good progress on coursework and good rest."},
            {"offset": 2, "mood": "Very Happy", "stress": 2, "energy": 9, "notes": "Celebrated semester project completion with friends!"},
            {"offset": 1, "mood": "Neutral", "stress": 5, "energy": 6, "notes": "Preparing study notes for finals review."},
            {"offset": 0, "mood": "Happy", "stress": 3, "energy": 8, "notes": "Feeling centered, calm, and prepared today."},
        ]

        for item in user_a_moods:
            rec_date = today - timedelta(days=item["offset"])
            m = MoodRecord(
                user_id=user_a.user_id,
                mood=item["mood"],
                stress_level=item["stress"],
                energy_level=item["energy"],
                notes=item["notes"],
                recorded_at=rec_date,
            )
            db.session.add(m)

        user_a_journals = [
            (
                "Reflections on Balance and Resilience",
                "Today I realized that when assignments pile up, my first instinct is to sacrifice sleep. "
                "However, protecting my rest actually saves hours of mental fatigue the next day. "
                "I am glad to have this encrypted space where I can record these thoughts in complete privacy."
            ),
            (
                "Small Wins Throughout the Week",
                "Managed to cook a balanced meal each day this week and kept up with my morning hydration routine. "
                "Even on intense exam days, taking just 10 minutes to step away from screens helped me maintain clarity."
            ),
        ]

        for title, raw_text in user_a_journals:
            encrypted_text = EncryptionService.encrypt(raw_text)
            j = JournalEntry(
                user_id=user_a.user_id,
                title=title,
                encrypted_content=encrypted_text,
            )
            db.session.add(j)

        db.session.commit()
        clear_explicit_rls_user()

        # Seed User B Records (Setting RLS context for User B)
        set_explicit_rls_user(user_b.user_id)
        if MoodRecord.query.filter_by(user_id=user_b.user_id).count() == 0:
            print("[*] Seeding records for User B...")

            user_b_moods = [
            {"offset": 5, "mood": "Neutral", "stress": 5, "energy": 5, "notes": "Quiet start to the week."},
            {"offset": 4, "mood": "Sad", "stress": 7, "energy": 4, "notes": "Felt tired after a long commute."},
            {"offset": 3, "mood": "Happy", "stress": 4, "energy": 7, "notes": "Reconnected with an old friend."},
            {"offset": 2, "mood": "Very Happy", "stress": 3, "energy": 8, "notes": "Enjoyed an outdoor hike."},
            {"offset": 0, "mood": "Happy", "stress": 4, "energy": 7, "notes": "Feeling refreshed and optimistic."},
        ]

        for item in user_b_moods:
            rec_date = today - timedelta(days=item["offset"])
            m = MoodRecord(
                user_id=user_b.user_id,
                mood=item["mood"],
                stress_level=item["stress"],
                energy_level=item["energy"],
                notes=item["notes"],
                recorded_at=rec_date,
            )
            db.session.add(m)

        user_b_journals = [
            (
                "New Routine Thoughts",
                "Starting to practice progressive muscle relaxation before bed. It seems to help relax my shoulder muscles after long typing sessions."
            )
        ]

        for title, raw_text in user_b_journals:
            encrypted_text = EncryptionService.encrypt(raw_text)
            j = JournalEntry(
                user_id=user_b.user_id,
                title=title,
                encrypted_content=encrypted_text,
            )
            db.session.add(j)

        db.session.commit()
        clear_explicit_rls_user()

        print("[+] Seeding completed successfully!")
        print("    Admin credentials: admin@mindguard.local / AdminPassword2026!")
        print("    User A credentials: alex@mindguard.local / UserA_Password2026!")
        print("    User B credentials: sam@mindguard.local / UserB_Password2026!")


if __name__ == "__main__":
    seed()
