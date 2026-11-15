-- MINDGUARD: Row-Level Security (RLS) Configuration
-- Applied by schema migrator or database owner to enforce table-level isolation

\connect mindguard_db

-- 1. MOOD RECORDS
ALTER TABLE mood_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE mood_records FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS mood_records_user_policy ON mood_records;
CREATE POLICY mood_records_user_policy ON mood_records
    FOR ALL
    TO mindguard_app
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

-- 2. JOURNAL ENTRIES
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS journal_entries_user_policy ON journal_entries;
CREATE POLICY journal_entries_user_policy ON journal_entries
    FOR ALL
    TO mindguard_app
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

-- 3. WELLNESS REPORTS
ALTER TABLE wellness_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE wellness_reports FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS wellness_reports_user_policy ON wellness_reports;
CREATE POLICY wellness_reports_user_policy ON wellness_reports
    FOR ALL
    TO mindguard_app
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

-- 4. USER SESSIONS
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_sessions_user_policy ON user_sessions;
CREATE POLICY user_sessions_user_policy ON user_sessions
    FOR ALL
    TO mindguard_app
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

-- 5. NOTIFICATIONS
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS notifications_user_policy ON notifications;
CREATE POLICY notifications_user_policy ON notifications
    FOR ALL
    TO mindguard_app
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

-- 6. NOTIFICATION PREFERENCES
ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_preferences FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS notification_preferences_user_policy ON notification_preferences;
CREATE POLICY notification_preferences_user_policy ON notification_preferences
    FOR ALL
    TO mindguard_app
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
