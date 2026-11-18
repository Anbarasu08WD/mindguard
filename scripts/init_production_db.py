"""One-time (and after every schema change) database setup for production.

Vercel functions skip database initialisation on purpose (cold starts must be fast and
the app role must not be able to alter the schema). Run this from your own computer,
pointing MIGRATION_DATABASE_URL at the production database:

    python scripts/init_production_db.py

It creates any missing tables (including notifications), applies the Row-Level Security
policies and grants, and verifies them, using the privileged migration role.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

# Force the non-production path, which runs init_db(); a deployed Vercel app never does this.
os.environ.pop("VERCEL", None)
os.environ.pop("VERCEL_ENV", None)

from app import create_app  # noqa: E402

if __name__ == "__main__":
    create_app("development")
    print("Database tables, RLS policies and grants are up to date.")
