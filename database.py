
import logging

from sqlalchemy import create_engine, text

from extensions import db
import models  # Register all SQLAlchemy models

logger = logging.getLogger(__name__)


def init_db(app):
    """
    Create database tables using the dedicated migration role,
    then apply and verify Row-Level Security policies.
    """
    migrator_url = app.config.get("MIGRATION_DATABASE_URL")

    if not migrator_url:
        raise RuntimeError(
            "MIGRATION_DATABASE_URL is missing. "
            "Database initialization requires the migration role."
        )

    engine = create_engine(
        migrator_url,
        pool_pre_ping=True,
    )

    try:
        with app.app_context():
            db.metadata.create_all(bind=engine)

        logger.info("All SQLAlchemy model tables verified or created.")

        apply_rls_policies(engine)

        logger.info("Database initialization and RLS setup completed.")

    finally:
        engine.dispose()


def apply_rls_policies(engine):
    """Apply RLS policies and application permissions atomically."""

    rls_commands = [
        # =====================================================
        # MOOD RECORDS
        # =====================================================

        """
        ALTER TABLE public.mood_records
        ENABLE ROW LEVEL SECURITY
        """,
        """
        ALTER TABLE public.mood_records
        FORCE ROW LEVEL SECURITY
        """,
        """
        DROP POLICY IF EXISTS mood_records_user_policy
        ON public.mood_records
        """,
        """
        CREATE POLICY mood_records_user_policy
        ON public.mood_records
        FOR ALL TO mindguard_app
        USING (
            user_id::text = current_setting('app.current_user_id', true)
        )
        WITH CHECK (
            user_id::text = current_setting('app.current_user_id', true)
        )
        """,

        # =====================================================
        # JOURNAL ENTRIES
        # =====================================================

        """
        ALTER TABLE public.journal_entries
        ENABLE ROW LEVEL SECURITY
        """,
        """
        ALTER TABLE public.journal_entries
        FORCE ROW LEVEL SECURITY
        """,
        """
        DROP POLICY IF EXISTS journal_entries_user_policy
        ON public.journal_entries
        """,
        """
        CREATE POLICY journal_entries_user_policy
        ON public.journal_entries
        FOR ALL TO mindguard_app
        USING (
            user_id::text = current_setting('app.current_user_id', true)
        )
        WITH CHECK (
            user_id::text = current_setting('app.current_user_id', true)
        )
        """,

        # =====================================================
        # WELLNESS REPORTS
        # =====================================================

        """
        ALTER TABLE public.wellness_reports
        ENABLE ROW LEVEL SECURITY
        """,
        """
        ALTER TABLE public.wellness_reports
        FORCE ROW LEVEL SECURITY
        """,
        """
        DROP POLICY IF EXISTS wellness_reports_user_policy
        ON public.wellness_reports
        """,
        """
        CREATE POLICY wellness_reports_user_policy
        ON public.wellness_reports
        FOR ALL TO mindguard_app
        USING (
            user_id::text = current_setting('app.current_user_id', true)
        )
        WITH CHECK (
            user_id::text = current_setting('app.current_user_id', true)
        )
        """,

        # =====================================================
        # USER SESSIONS
        # =====================================================

        """
        ALTER TABLE public.user_sessions
        ENABLE ROW LEVEL SECURITY
        """,
        """
        ALTER TABLE public.user_sessions
        FORCE ROW LEVEL SECURITY
        """,
        """
        DROP POLICY IF EXISTS user_sessions_user_policy
        ON public.user_sessions
        """,
        """
        CREATE POLICY user_sessions_user_policy
        ON public.user_sessions
        FOR ALL TO mindguard_app
        USING (
            user_id::text = current_setting('app.current_user_id', true)
        )
        WITH CHECK (
            user_id::text = current_setting('app.current_user_id', true)
        )
        """,

        # =====================================================
        # USER CONSENTS
        # =====================================================

        """
        ALTER TABLE public.user_consents
        ENABLE ROW LEVEL SECURITY
        """,
        """
        ALTER TABLE public.user_consents
        FORCE ROW LEVEL SECURITY
        """,
        """
        DROP POLICY IF EXISTS user_consents_user_policy
        ON public.user_consents
        """,
        """
        CREATE POLICY user_consents_user_policy
        ON public.user_consents
        FOR ALL TO mindguard_app
        USING (
            user_id::text = current_setting('app.current_user_id', true)
        )
        WITH CHECK (
            user_id::text = current_setting('app.current_user_id', true)
        )
        """,

        # =====================================================
        # NOTIFICATIONS
        # =====================================================

        """
        ALTER TABLE public.notifications
        ENABLE ROW LEVEL SECURITY
        """,
        """
        ALTER TABLE public.notifications
        FORCE ROW LEVEL SECURITY
        """,
        """
        DROP POLICY IF EXISTS notifications_user_policy
        ON public.notifications
        """,
        """
        CREATE POLICY notifications_user_policy
        ON public.notifications
        FOR ALL TO mindguard_app
        USING (
            user_id::text = current_setting('app.current_user_id', true)
        )
        WITH CHECK (
            user_id::text = current_setting('app.current_user_id', true)
        )
        """,

        # =====================================================
        # NOTIFICATION PREFERENCES
        # =====================================================

        """
        ALTER TABLE public.notification_preferences
        ENABLE ROW LEVEL SECURITY
        """,
        """
        ALTER TABLE public.notification_preferences
        FORCE ROW LEVEL SECURITY
        """,
        """
        DROP POLICY IF EXISTS notification_preferences_user_policy
        ON public.notification_preferences
        """,
        """
        CREATE POLICY notification_preferences_user_policy
        ON public.notification_preferences
        FOR ALL TO mindguard_app
        USING (
            user_id::text = current_setting('app.current_user_id', true)
        )
        WITH CHECK (
            user_id::text = current_setting('app.current_user_id', true)
        )
        """,

        # =====================================================
        # AUDIT LOGS
        # =====================================================

        """
        ALTER TABLE public.audit_logs
        ENABLE ROW LEVEL SECURITY
        """,
        """
        ALTER TABLE public.audit_logs
        FORCE ROW LEVEL SECURITY
        """,
        """
        DROP POLICY IF EXISTS audit_logs_admin_select
        ON public.audit_logs
        """,
        """
        CREATE POLICY audit_logs_admin_select
        ON public.audit_logs
        FOR SELECT TO mindguard_app
        USING (
            public.auth_is_active_admin()
        )
        """,
        """
        DROP POLICY IF EXISTS audit_logs_insert
        ON public.audit_logs
        """,
        """
        CREATE POLICY audit_logs_insert
        ON public.audit_logs
        FOR INSERT TO mindguard_app
        WITH CHECK (true)
        """,

        # =====================================================
        # WELLNESS SUGGESTIONS
        # =====================================================

        """
        ALTER TABLE public.wellness_suggestions
        ENABLE ROW LEVEL SECURITY
        """,
        """
        ALTER TABLE public.wellness_suggestions
        FORCE ROW LEVEL SECURITY
        """,
        """
        DROP POLICY IF EXISTS wellness_suggestions_read_policy
        ON public.wellness_suggestions
        """,
        """
        CREATE POLICY wellness_suggestions_read_policy
        ON public.wellness_suggestions
        FOR SELECT TO mindguard_app
        USING (true)
        """,

        # =====================================================
        # USERS
        # =====================================================

        """
        ALTER TABLE public.users
        ENABLE ROW LEVEL SECURITY
        """,
        """
        ALTER TABLE public.users
        FORCE ROW LEVEL SECURITY
        """,

        # Users can read their own record.
        # Active administrators can read all user records.
        """
        DROP POLICY IF EXISTS users_select_policy
        ON public.users
        """,
        """
        CREATE POLICY users_select_policy
        ON public.users
        FOR SELECT TO mindguard_app
        USING (
            user_id::text = current_setting('app.current_user_id', true)
            OR public.auth_is_active_admin()
        )
        """,

        # Registration can create only an ordinary active account
        # belonging to the current RLS identity.
        """
        DROP POLICY IF EXISTS users_insert_policy
        ON public.users
        """,
        """
        CREATE POLICY users_insert_policy
        ON public.users
        FOR INSERT TO mindguard_app
        WITH CHECK (
            user_id::text = current_setting('app.current_user_id', true)
            AND role = 'user'
            AND account_status = 'active'
        )
        """,

        # Users can update their own row.
        # Active administrators can update rows too,
        # subject to column-level UPDATE permissions.
        """
        DROP POLICY IF EXISTS users_update_policy
        ON public.users
        """,
        """
        CREATE POLICY users_update_policy
        ON public.users
        FOR UPDATE TO mindguard_app
        USING (
            user_id::text = current_setting('app.current_user_id', true)
            OR public.auth_is_active_admin()
        )
        WITH CHECK (
            user_id::text = current_setting('app.current_user_id', true)
            OR public.auth_is_active_admin()
        )
        """,

        # =====================================================
        # RESTRICT APPLICATION PERMISSIONS
        # =====================================================

        # Audit logs cannot be modified or deleted by the app.
        """
        REVOKE UPDATE, DELETE
        ON TABLE public.audit_logs
        FROM mindguard_app
        """,

        # Wellness suggestions are read-only for the app.
        """
        REVOKE INSERT, UPDATE, DELETE
        ON TABLE public.wellness_suggestions
        FROM mindguard_app
        """,

        # Remove table-level UPDATE permission on users.
        """
        REVOKE UPDATE
        ON TABLE public.users
        FROM mindguard_app
        """,

        # Remove existing column-level UPDATE permissions.
        """
        REVOKE UPDATE (
            user_id,
            full_name,
            email,
            password_hash,
            role,
            account_status,
            created_at,
            updated_at
        )
        ON TABLE public.users
        FROM mindguard_app
        """,

        # Permit updates only to profile name, password hash,
        # and modification timestamp.
        """
        GRANT UPDATE (
            full_name,
            password_hash,
            updated_at
        )
        ON TABLE public.users
        TO mindguard_app
        """,

        # The app must never directly delete user records.
        """
        REVOKE DELETE
        ON TABLE public.users
        FROM mindguard_app
        """,
    ]

    # =========================================================
    # APPLY AND VERIFY EVERYTHING IN ONE TRANSACTION
    # =========================================================

    with engine.begin() as conn:

        for command in rls_commands:
            conn.execute(text(command))

        expected_tables = {
            "users",
            "mood_records",
            "journal_entries",
            "wellness_reports",
            "user_sessions",
            "user_consents",
            "audit_logs",
            "wellness_suggestions",
            "notifications",
            "notification_preferences",
        }

        result = conn.execute(
            text("""
                SELECT
                    tablename,
                    rowsecurity,
                    (
                        SELECT c.relforcerowsecurity
                        FROM pg_class c
                        JOIN pg_namespace n
                            ON n.oid = c.relnamespace
                        WHERE n.nspname = 'public'
                          AND c.relname = t.tablename
                    ) AS forced
                FROM pg_tables t
                WHERE schemaname = 'public'
                  AND tablename IN (
                      'users',
                      'mood_records',
                      'journal_entries',
                      'wellness_reports',
                      'user_sessions',
                      'user_consents',
                      'audit_logs',
                      'wellness_suggestions',
                      'notifications',
                      'notification_preferences'
                  )
                ORDER BY tablename
            """)
        ).fetchall()

        verified_tables = {
            row.tablename
            for row in result
            if row.rowsecurity and row.forced
        }

        if verified_tables != expected_tables:
            raise RuntimeError(
                "RLS verification failed. "
                f"Expected {expected_tables}, got {verified_tables}"
            )

        # Verify restricted UPDATE privileges.
        update_permissions = {
            column: conn.execute(
                text("""
                    SELECT has_column_privilege(
                        'mindguard_app',
                        'public.users',
                        :column_name,
                        'UPDATE'
                    )
                """),
                {"column_name": column},
            ).scalar_one()
            for column in (
                "full_name",
                "password_hash",
                "updated_at",
                "role",
                "account_status",
                "email",
                "created_at",
                "user_id",
            )
        }

        expected_update_permissions = {
            "full_name": True,
            "password_hash": True,
            "updated_at": True,
            "role": False,
            "account_status": False,
            "email": False,
            "created_at": False,
            "user_id": False,
        }

        if update_permissions != expected_update_permissions:
            raise RuntimeError(
                "Users column permission verification failed. "
                f"Expected {expected_update_permissions}, "
                f"got {update_permissions}"
            )

    logger.info(
        "RLS enabled and forced on all ten sensitive tables."
    )
    logger.info(
        "Users UPDATE permissions restricted to approved columns."
    )
