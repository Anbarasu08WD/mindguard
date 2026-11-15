-- MINDGUARD: Database & Schema Security Setup Script
-- Run this as postgres superuser connected to mindguard_db

ALTER DATABASE mindguard_db OWNER TO mindguard_owner;

\connect mindguard_db

-- Secure public schema
GRANT USAGE, CREATE ON SCHEMA public TO mindguard_owner;
GRANT USAGE, CREATE ON SCHEMA public TO mindguard_migrator;
GRANT USAGE ON SCHEMA public TO mindguard_app;

-- Default permissions for tables and sequences created by owner or migrator
ALTER DEFAULT PRIVILEGES FOR ROLE mindguard_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mindguard_app;

ALTER DEFAULT PRIVILEGES FOR ROLE mindguard_owner IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO mindguard_app;

ALTER DEFAULT PRIVILEGES FOR ROLE mindguard_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mindguard_app;

ALTER DEFAULT PRIVILEGES FOR ROLE mindguard_migrator IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO mindguard_app;

-- Verify restricted role has NO superuser and NO bypassrls
ALTER ROLE mindguard_app NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
