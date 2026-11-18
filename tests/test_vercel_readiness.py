"""Tests for the Vercel deployment fixes (pure, no database needed)."""
import json
import os
import re
from datetime import date

import config
import timeutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_database_urls_are_normalised_for_psycopg3():
    f = config._normalize_db_url
    assert f("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert f("postgresql://u:p@host/db?sslmode=require") == "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert f("postgresql+psycopg://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert f("  postgres://u:p@host/db  ") == "postgresql+psycopg://u:p@host/db"
    assert f("") == "" and f(None) is None


def test_engine_options_disable_prepared_statements_for_poolers():
    assert config.Config.SQLALCHEMY_ENGINE_OPTIONS["connect_args"]["prepare_threshold"] is None


def test_production_cookies_are_secure():
    assert config.ProductionConfig.SESSION_COOKIE_SECURE is True
    assert config.ProductionConfig.REMEMBER_COOKIE_SECURE is True


def test_timeutil_uses_app_timezone_and_falls_back(monkeypatch):
    monkeypatch.delenv("APP_TIMEZONE", raising=False)
    assert isinstance(timeutil.local_today(), date)
    monkeypatch.setenv("APP_TIMEZONE", "Pacific/Kiritimati")      # UTC+14
    monkeypatch.setenv("APP_TIMEZONE", "Not/AZone")                # invalid -> safe fallback
    assert isinstance(timeutil.local_today(), date)


def test_static_templates_have_a_static_endpoint_in_every_environment():
    """Regression for the Vercel 500: static_folder=None removed the 'static' endpoint."""
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    assert "static_folder=None" not in src
    assert 'static_folder=os.path.join(base_dir, "public", "static")' in src
    assert os.path.isdir(os.path.join(ROOT, "public", "static", "css"))


def test_every_static_file_referenced_by_templates_exists():
    pattern = re.compile(r"url_for\(\s*['\"]static['\"]\s*,\s*filename\s*=\s*['\"]([^'\"]+)['\"]")
    missing = []
    for folder, _, files in os.walk(os.path.join(ROOT, "templates")):
        for name in files:
            text = open(os.path.join(folder, name), encoding="utf-8").read()
            for rel in pattern.findall(text):
                if not os.path.isfile(os.path.join(ROOT, "public", "static", rel)):
                    missing.append(rel)
    assert not missing, f"Templates reference missing static files: {missing}"


def test_vercel_files_are_valid():
    cfg = json.load(open(os.path.join(ROOT, "vercel.json"), encoding="utf-8"))
    assert "app.py" in cfg["functions"]
    ignore = open(os.path.join(ROOT, ".vercelignore"), encoding="utf-8").read()
    assert ".env" in ignore and "venv/" in ignore


def test_runtime_requirements_have_no_test_tooling_and_include_tzdata():
    reqs = open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8").read().lower()
    assert "pytest" not in reqs and "gunicorn" not in reqs
    assert "tzdata" in reqs and "psycopg" in reqs
