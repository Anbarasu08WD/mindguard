# MINDGUARD

> **"Your Mental Wellness. Your Privacy. Your Control."**
> 
> *Privacy-Preserving Mental Wellness Monitoring System Using Relational Database Security Mechanisms*  
> **Academic Project:** B.Tech Information Technology Capstone Project

---

## 1. Executive Summary & Objective

**MindGuard** is a full-stack, privacy-preserving mental wellness self-monitoring web application engineered with Python Flask and PostgreSQL 18. The system enables individuals to track emotional trends, stress levels, energy patterns, and personal journal reflections without exposing intimate psychological logs to invasive data harvesting, administrative surveillance, or arbitrary database queries.

### Core Academic Highlight
The primary innovation of MindGuard is demonstrating **how relational database security mechanisms can enforce personal privacy at the database kernel level**:
1. **PostgreSQL Row-Level Security (RLS)**: Enforces row-level isolation inside the PostgreSQL database engine using transaction-scoped settings (`SET LOCAL app.current_user_id`), ensuring queries without application-level `WHERE` filters physically cannot access other users' rows.
2. **Restricted Application Role (`mindguard_app`)**: Runs with strictly `NOSUPERUSER` and `NOBYPASSRLS` privileges, eliminating the common vulnerability of applications connecting as database superusers.
3. **Cryptographic Field-Level Encryption**: Private journal reflections are encrypted using Python Cryptography **Fernet** (authenticated 128-bit AES in CBC mode with HMAC SHA-256) prior to database insertion; ciphertext is stored on disk, and plaintext is only decrypted in the authenticated owner's authorized session.
4. **Role-Based Access Control (RBAC)**: Separates User and Administrator capabilities. Administrators monitor aggregated system health and audit logs, but are strictly prohibited from viewing individual mood check-ins or private journal entries.
5. **Non-Clinical Disclaimer**: MindGuard is a self-monitoring platform designed for personal wellness awareness and reflection; it does not claim to diagnose or treat psychiatric or medical conditions.

---

## 2. Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Chart.js 4.4, Lucide Icons, Google Fonts (Inter, Poppins) |
| **Backend** | Python 3.14+, Flask 3.1, Flask Blueprints, Flask-Login, Flask-WTF (CSRF), Werkzeug Security, Flask-Limiter |
| **Database** | PostgreSQL 18, `psycopg` (v3 binary driver), SQLAlchemy ORM 2.1, Flask-Migrate, Alembic |
| **Cryptography & Security** | Python `cryptography` (Fernet), PBKDF2 SHA-256 password hashing, transaction-scoped PostgreSQL settings |
| **Testing** | Pytest, Pytest-Flask (82 automated security and functional tests) |
| **Deployment** | Gunicorn WSGI, production environment configuration, security headers (CSP, HSTS, X-Frame-Options) |

---

## 3. Relational Database Architecture

MindGuard utilizes **PostgreSQL 18** with 8 relational tables and 3 isolated database roles.

### A. Isolated Database Roles
- **`mindguard_owner`**: Database and schema owner; executes initial schema creation and administrative setup.
- **`mindguard_migrator`**: Role dedicated to executing Alembic / Flask-Migrate schema migrations with DDL privileges.
- **`mindguard_app`**: Restricted application runtime role. Bound by `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, and `NOBYPASSRLS`.

### B. Relational Schema Tables
1. **`users`**: User identity, full name, unique email, Werkzeug PBKDF2 password hash, role (`user` / `admin`), account status (`active` / `disabled`), timestamps.
2. **`mood_records`** *(RLS Enabled & Forced)*: `record_id`, `user_id` (FK), `mood`, `stress_level` (CHECK 1-10), `energy_level` (CHECK 1-10), `notes`, `recorded_at`, `created_at`. Unique constraint enforces 1 check-in per user per day.
3. **`journal_entries`** *(RLS Enabled & Forced)*: `journal_id`, `user_id` (FK), `title`, `encrypted_content` (Fernet base64 ciphertext), timestamps.
4. **`wellness_reports`** *(RLS Enabled & Forced)*: `report_id`, `user_id` (FK), `report_date`, `report_summary`, `created_at`.
5. **`wellness_suggestions`**: Curated supportive activities across Mindfulness, Relaxation, Healthy Routines, Journaling, Physical Activity, Study-Life Balance.
6. **`audit_logs`**: Security events (`action`, `event_status`, `user_id`, `timestamp`, `ip_address`). Passwords, keys, and journal texts are never logged.
7. **`user_consents`**: Granular consent preferences (`privacy_policy`, `wellness_analytics`, `data_storage`) with status and timestamps.
8. **`user_sessions`** *(RLS Enabled & Forced)*: Persistent session tracking, SHA-256 session token hashes, expiration, and revocation timestamps.

### C. Row-Level Security (RLS) Policy Implementation
```sql
-- Enforced directly within PostgreSQL kernel
ALTER TABLE mood_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE mood_records FORCE ROW LEVEL SECURITY;

CREATE POLICY mood_records_user_policy ON mood_records
    FOR ALL TO mindguard_app
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

-- Executed transaction-scoped by SQLAlchemy hook:
SELECT set_config('app.current_user_id', :uid, true);
```

---

## 4. Project Directory Structure

```text
mindguard/
├── app.py                      # Application factory, routes registration, security headers, error handlers
├── config.py                   # Development, Testing, and Production configuration classes
├── extensions.py               # Extensions init: db, login_manager, csrf, limiter, migrate
├── database.py                 # DB schema initialization and RLS policy applicator
├── requirements.txt            # Python dependencies
├── .env.example                # Template for environment configuration
├── .env                        # Local environment secrets (excluded from git)
├── .gitignore                  # Git ignore rules
├── README.md                   # Complete documentation
│
├── models/                     # SQLAlchemy Models
│   ├── __init__.py
│   ├── user.py                 # User model with Werkzeug password hashing
│   ├── mood.py                 # MoodRecord with 1-10 checks & unique day constraint
│   ├── journal.py              # JournalEntry with encrypted_content
│   ├── report.py               # WellnessReport model
│   ├── suggestion.py           # WellnessSuggestion model
│   ├── audit.py                # AuditLog model
│   ├── consent.py              # UserConsent model
│   └── session.py              # UserSession model
│
├── routes/                     # Modular Flask Blueprints
│   ├── __init__.py
│   ├── auth.py                 # /register, /login, /logout, session tracking
│   ├── dashboard.py            # /dashboard user wellness overview
│   ├── mood.py                 # /mood CRUD, sliders, date filters
│   ├── journal.py              # /journal encrypted reflections CRUD
│   ├── analytics.py            # /analytics, /api/analytics endpoints
│   ├── suggestions.py          # /suggestions rule-based recommendations & guided timer
│   ├── privacy.py              # /privacy console, /export (JSON), /delete-account
│   ├── profile.py              # /profile details, password update, session revocation
│   └── admin.py                # /admin dashboard, /users management, /audit-logs
│
├── services/                   # Business Logic & Security Services
│   ├── __init__.py
│   ├── encryption_service.py   # Fernet field-level encryption/decryption
│   ├── database_security.py    # PostgreSQL RLS transaction hook & context sync
│   ├── audit_service.py        # Sanitized security auditing
│   ├── security_service.py     # RBAC decorators & password strength validation
│   ├── analytics_service.py    # Statistical aggregation & trend calculations
│   └── recommendation_service.py # Rule-based self-care matching
│
├── templates/                  # Jinja2 HTML Templates
│   ├── base.html               # Public base layout, fonts, CDNs, header/footer
│   ├── dashboard_base.html     # Authenticated app layout with sidebar & topbar
│   ├── index.html              # Commercial-grade SaaS landing page (Module 1)
│   ├── auth/                   # Login & registration views
│   ├── dashboard/              # User dashboard view
│   ├── mood/                   # Mood check-in history & interactive form
│   ├── journal/                # Journal entries list & encrypted reflection form
│   ├── analytics/              # Chart.js analytics dashboard
│   ├── suggestions/            # Self-care suggestions & guided timer modal
│   ├── privacy/                # Privacy console, consent settings & account purge
│   ├── profile/                # Profile management & active sessions
│   ├── admin/                  # Administrative overview, users list & audit logs
│   └── errors/                 # Custom error pages: 400, 401, 403, 404, 500
│
├── static/                     # Static Assets
│   ├── css/
│   │   ├── style.css           # Core design system & theme variables
│   │   ├── dashboard.css       # Sidebar, cards, widgets, and modal styles
│   │   └── responsive.css      # Mobile and tablet breakpoints
│   └── js/
│       ├── main.js             # Lucide icons, alert dismissals, password toggles
│       ├── mood.js             # Emoji selector & dynamic slider pills
│       ├── analytics.js        # Chart.js line, bar, and doughnut charts
│       └── dashboard.js        # Dashboard mini-trend chart & activity modal
│
├── scripts/                    # Database Setup & Seeding Scripts
│   ├── create_roles.sql        # Creates mindguard_owner, mindguard_migrator, mindguard_app
│   ├── setup_database.sql      # Database schema privileges & role configurations
│   ├── apply_rls.sql           # Direct SQL script to enable & force PostgreSQL RLS
│   └── seed.py                 # Database seeding script with realistic sample data
│
└── tests/                      # Automated Pytest Suite (82 Tests)
    ├── conftest.py             # Test fixtures & testing app configuration
    ├── test_auth.py            # Registration, login, password checks, logout
    ├── test_mood.py            # Mood CRUD, slider bounds, date validation
    ├── test_journal.py         # Fernet encryption verification & CRUD
    ├── test_authorization.py   # Mandatory User A vs User B cross-access denial
    ├── test_rls.py             # Direct engine test using restricted mindguard_app role
    └── test_security.py        # SQLi defense, CSRF, audit log, JSON export, cascade delete
```

---

## 5. Step-by-Step Installation & Setup (Windows PowerShell)

### Prerequisites
- **Python 3.11+** installed (tested on Python 3.14.6)
- **PostgreSQL 16+** installed and running as a Windows service (tested on PostgreSQL 18.6)
- Standard Windows PowerShell terminal

---

### Step 1: Open PowerShell and Navigate to Workspace
```powershell
cd C:\Users\Anbarasu\Documents\mindgaurd
```

### Step 2: Create and Activate Python Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Database and Isolated Roles
Run the SQL scripts using PostgreSQL `psql` (substitute your postgres superuser password when prompted or set `$env:PGPASSWORD`):
```powershell
# 1. Create mindguard_db and isolated roles (mindguard_owner, mindguard_migrator, mindguard_app)
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -p 5432 -f ".\scripts\create_roles.sql"

# 2. Configure schema privileges and default permissions
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -p 5432 -f ".\scripts\setup_database.sql"
```

### Step 5: Configure Environment Variables
Generate secure keys and verify `.env`:
```powershell
# Generate Secret Key and Fernet Key via Python
python -c "import secrets; from cryptography.fernet import Fernet; print('SECRET_KEY=' + secrets.token_hex(32)); print('FERNET_KEY=' + Fernet.generate_key().decode())"
```
Ensure your `.env` contains:
```ini
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=feed62e7e35b97be14457701e8bc7d3da7909f4b0155c9c6c33b48fa56fbe420
DATABASE_URL=postgresql+psycopg://mindguard_app:MindGuardApp2026!@localhost:5432/mindguard_db
MIGRATION_DATABASE_URL=postgresql+psycopg://mindguard_migrator:MindGuardMigrator2026!@localhost:5432/mindguard_db
FERNET_KEY=zn5ZY7pqOZP_aEP8H1px3oLyYY_TTte-tDadH-t35HM=

DB_HOST=localhost
DB_PORT=5432
DB_NAME=mindguard_db
DB_USER=mindguard_app
DB_PASSWORD=MindGuardApp2026!
```

### Step 6: Initialize and Apply Database Migrations
```powershell
# Migrations are managed with Alembic via the migrator role
flask db upgrade
```

### Step 7: Seed Sample Development Accounts & Records
```powershell
python scripts/seed.py
```

### Step 8: Run Automated Tests
```powershell
pytest -v
```
*Expected: 82 passed.*

### Step 9: Launch the Application
```powershell
python app.py
```
Open your browser and navigate to:  
👉 **`http://127.0.0.1:5000`**

---

## 6. Preconfigured Development Accounts

| Account Role | Email Address | Password | Permissions & Purpose |
|---|---|---|---|
| **Administrator** | `admin@mindguard.local` | `AdminPassword2026!` | Access `/admin`, manage accounts, review security audit logs. Strictly blocked from viewing user journals or individual mood check-ins. |
| **User A (Alex Rivera)** | `alex@mindguard.local` | `UserA_Password2026!` | Full standard user with 11 pre-seeded daily check-ins across 10 days and 2 Fernet-encrypted journal reflections. |
| **User B (Sam Taylor)** | `sam@mindguard.local` | `UserB_Password2026!` | Independent standard user with 5 pre-seeded daily check-ins and 1 encrypted reflection. |

---

## 7. Automated Testing Suite & Verification

The project includes 82 comprehensive automated tests (the list below shows the original core suite) executed with `pytest`:

```text
tests/test_auth.py::test_user_registration PASSED                        [  4%]
tests/test_auth.py::test_duplicate_email_prevention PASSED               [  9%]
tests/test_auth.py::test_password_strength_validation PASSED             [ 14%]
tests/test_auth.py::test_login_success_and_logout PASSED                 [ 19%]
tests/test_auth.py::test_login_invalid_password PASSED                   [ 23%]
tests/test_auth.py::test_unauthenticated_dashboard_access PASSED         [ 28%]
tests/test_authorization.py::test_cross_user_isolation_user_a_and_user_b PASSED [ 33%]
tests/test_authorization.py::test_rbac_standard_user_blocked_from_admin PASSED [ 38%]
tests/test_authorization.py::test_rbac_admin_allowed_on_admin_dashboard PASSED [ 42%]
tests/test_journal.py::test_journal_encryption_and_decryption PASSED     [ 47%]
tests/test_journal.py::test_journal_edit_and_delete PASSED               [ 52%]
tests/test_mood.py::test_mood_creation_and_ownership PASSED              [ 57%]
tests/test_mood.py::test_mood_validation_ranges PASSED                   [ 61%]
tests/test_mood.py::test_mood_edit_and_delete PASSED                     [ 66%]
tests/test_rls.py::test_restricted_role_privileges PASSED                [ 71%]
tests/test_rls.py::test_rls_direct_isolation PASSED                      [ 76%]
tests/test_security.py::test_sql_injection_defense PASSED                [ 80%]
tests/test_security.py::test_audit_logging_and_sanitization PASSED       [ 85%]
tests/test_security.py::test_data_export PASSED                          [ 90%]
tests/test_security.py::test_account_deletion_cascade PASSED             [ 95%]
tests/test_security.py::test_invalid_account_deletion_confirmation PASSED [100%]

============================= 21 passed in 7.13s ==============================
```

### Mandatory Scenario Result
- **User A** creates mood check-in and encrypted journal reflection.
- **User B** logs in and attempts to read, edit, or delete User A's mood and journal entries.
- **Result:** Both backend authorization logic and PostgreSQL Row-Level Security policies immediately deny the requests (`403 Forbidden` / 0 records returned).

---

## 8. Security Mechanisms Summary

1. **PostgreSQL Row-Level Security (RLS)**: Sensitive tables (`mood_records`, `journal_entries`, `wellness_reports`, `user_sessions`) enforce kernel-level isolation matching `current_setting('app.current_user_id', true)`.
2. **Restricted Application Database Role**: The app connects as `mindguard_app` with `NOSUPERUSER` and `NOBYPASSRLS`.
3. **Fernet Authenticated Encryption**: Journal bodies are encrypted using 128-bit AES in CBC mode with HMAC SHA-256 before disk writes.
4. **Password Hashing**: Passwords stored exclusively as Werkzeug PBKDF2 SHA-256 hashes.
5. **SQL Injection Defense**: 100% parameterized queries via SQLAlchemy ORM; user inputs are never concatenated into raw SQL.
6. **Cross-Site Request Forgery (CSRF)**: Enforced across all state-changing `POST` requests via Flask-WTF.
7. **Rate Limiting**: Applied via Flask-Limiter (`20 per minute` on login, `15 per hour` on registration).
8. **Security Headers**: Injected via Flask `after_request` (Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Referrer-Policy).
9. **Audit Trail**: High-risk events (login success/failure, profile changes, account deletions) are logged without exposing sensitive notes or keys.
10. **Data Sovereignty**: Machine-readable JSON export and irreversible cascading account purge.

---

## 9. Deployment Readiness (Production)

To run MindGuard in production:
1. Set `FLASK_ENV=production` in `.env`.
2. Set `SESSION_COOKIE_SECURE=True` and ensure SSL/TLS certificates (HTTPS) are active.
3. Serve using Gunicorn behind an Nginx reverse proxy:
```bash
gunicorn -w 4 -b 127.0.0.1:5000 "app:create_app('production')"
```
4. Never expose port 5432 of PostgreSQL directly to the public internet.

---

## 10. License & Academic Attribution
Developed as an academic capstone project in **Information Technology**. Designed and implemented to demonstrate state-of-the-art privacy-preserving database security and full-stack software engineering.

---

## Additional Features (v1.1)

| Area | What was added |
|---|---|
| **UI/UX** | New design system (Plus Jakarta Sans + Inter, teal/cream palette), app shell with sidebar and top bar, redesigned landing, dashboard and auth pages, responsive layout |
| **Mood analytics** | Check-in streaks, consistency rate, weekday mood heatmap, mood/stress correlation, CSV export (own data, no notes) |
| **Journal** | Stats, sorting, word count and reading time, writing prompts, Markdown export (decrypted for the owner, audit-logged) |
| **Wellness insights** | Local, explainable insight engine with "Why am I seeing this?" evidence, weekly report saved to `wellness_reports`. No external AI service receives user data |
| **Notifications** | In-app bell and page: daily reminder, streak milestones, weekly summary, security alerts. New tables `notifications` and `notification_preferences`, both with FORCE Row-Level Security |
| **Admin dashboard** | Live RLS/role verification from PostgreSQL catalogs, signup and security-event charts, top audit actions, audit filters (date range), pagination and CSV export. Still aggregate-only |

**Database note:** the two new tables are created automatically on start-up by `init_db()`, and their RLS policies are applied by `apply_rls_policies()`. `scripts/apply_rls.sql` was updated for manual setups.

---

## Deploying to Vercel

**Project layout for Vercel:** `app.py` exposes the Flask `app`; static files live in `public/static` (Vercel serves `public/` from its CDN at the site root, Flask serves the same folder locally); `vercel.json` and `.vercelignore` keep the bundle small.

**1. Database (one time, from your own computer).** Vercel functions do not create tables or policies. Point `MIGRATION_DATABASE_URL` in your local `.env` at the *production* database and run:

```bash
python scripts/init_production_db.py
```

Re-run it whenever the schema changes (for example after adding tables).

**2. Environment variables** (Vercel > Project > Settings > Environment Variables, then redeploy):

| Variable | Value |
|---|---|
| `SECRET_KEY` | long random string |
| `FERNET_KEY` | the same key your journal entries were encrypted with |
| `DATABASE_URL` | connection string for the restricted `mindguard_app` role (a pooled/serverless URL is recommended) |
| `APP_TIMEZONE` | e.g. `Asia/Kolkata`, so "today", streaks and reminders use your local day |

`postgres://` and `postgresql://` URLs are converted automatically. `MIGRATION_DATABASE_URL` is **not** needed on Vercel.

**3. Notes**
- Rate limits use in-memory storage, so they apply per serverless instance. For strict global limits use Redis (`RATELIMIT_STORAGE_URI`).
- Never commit `.env`. Use `requirements-dev.txt` locally to install the test tools (`pytest`).
- If a deployment fails, open Vercel > Logs. A missing variable is reported by name at start-up.
