import pytest
from sqlalchemy import text, create_engine
from config import Config


def test_restricted_role_privileges():
    """Verify mindguard_app is strictly non-superuser and cannot bypass RLS."""
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'mindguard_app';")
        ).fetchone()

        assert res is not None
        rolsuper, rolbypassrls = res
        assert rolsuper is False, "Application role must not be a superuser"
        assert rolbypassrls is False, "Application role must NOT have BYPASSRLS privilege"


def test_rls_direct_isolation(user_a, user_b, db_session):
    """
    Direct PostgreSQL test verifying Row-Level Security at the database engine level.
    Uses the restricted mindguard_app connection.
    """
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

    # 1. Without setting app.current_user_id, no rows should be returned from protected tables
    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM mood_records;")).scalar()
        assert count == 0, "Without session context, RLS must block all rows"

    # 2. When transaction context is set to User A, only User A's rows are visible
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(
                text("SELECT set_config('app.current_user_id', :uid, true);"),
                {"uid": str(user_a.user_id)}
            )
            # Insert User A record directly
            conn.execute(
                text("""
                    INSERT INTO mood_records (user_id, mood, stress_level, energy_level, recorded_at, created_at)
                    VALUES (:uid, 'Happy', 4, 7, CURRENT_DATE, CURRENT_TIMESTAMP);
                """),
                {"uid": user_a.user_id}
            )

            # Query should see 1 record
            a_count = conn.execute(text("SELECT count(*) FROM mood_records;")).scalar()
            assert a_count >= 1

    # 3. When querying as User B, User A's record must be completely invisible
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(
                text("SELECT set_config('app.current_user_id', :uid, true);"),
                {"uid": str(user_b.user_id)}
            )
            b_count = conn.execute(text("SELECT count(*) FROM mood_records;")).scalar()
            # User B has no records inserted yet in this test connection
            assert b_count == 0

    # 4. Attempting to insert a row for User B while context is User A must be rejected by PostgreSQL RLS
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(
                text("SELECT set_config('app.current_user_id', :uid, true);"),
                {"uid": str(user_a.user_id)}
            )
            with pytest.raises(Exception) as exc_info:
                conn.execute(
                    text("""
                        INSERT INTO mood_records (user_id, mood, stress_level, energy_level, recorded_at, created_at)
                        VALUES (:imposter_uid, 'Sad', 8, 3, CURRENT_DATE + 1, CURRENT_TIMESTAMP);
                    """),
                    {"imposter_uid": user_b.user_id}
                )
            assert "violates row-level security policy" in str(exc_info.value).lower()
