-- MINDGUARD: Role Creation Script
-- Run this as postgres superuser to create isolated database roles

-- 1. Create database if not exists
SELECT 'CREATE DATABASE mindguard_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mindguard_db')\gexec

-- 2. Create Owner Role (Schema administration)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mindguard_owner') THEN
        CREATE ROLE mindguard_owner WITH LOGIN PASSWORD 'MindGuardOwner2026!';
    ELSE
        ALTER ROLE mindguard_owner WITH PASSWORD 'MindGuardOwner2026!';
    END IF;
END $$;

-- 3. Create Migrator Role (Schema migration permissions)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mindguard_migrator') THEN
        CREATE ROLE mindguard_migrator WITH LOGIN PASSWORD 'MindGuardMigrator2026!';
    ELSE
        ALTER ROLE mindguard_migrator WITH PASSWORD 'MindGuardMigrator2026!';
    END IF;
END $$;

-- 4. Create Restricted Application Role (Strictly NOSUPERUSER and NOBYPASSRLS)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mindguard_app') THEN
        CREATE ROLE mindguard_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS PASSWORD 'MindGuardApp2026!';
    ELSE
        ALTER ROLE mindguard_app WITH NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS PASSWORD 'MindGuardApp2026!';
    END IF;
END $$;

-- Grant database connect permissions
GRANT CONNECT ON DATABASE mindguard_db TO mindguard_owner;
GRANT CONNECT ON DATABASE mindguard_db TO mindguard_migrator;
GRANT CONNECT ON DATABASE mindguard_db TO mindguard_app;
