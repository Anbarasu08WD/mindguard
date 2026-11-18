import os
import time
from database import init_db
from flask import Flask, render_template, redirect, url_for, request, session
from werkzeug.middleware.proxy_fix import ProxyFix
from config import config_by_name
from extensions import db, login_manager, csrf, limiter, migrate
from models.user import User
from services.database_security import register_rls_listeners
from routes import (
    auth_bp,
    dashboard_bp,
    mood_bp,
    journal_bp,
    analytics_bp,
    suggestions_bp,
    privacy_bp,
    profile_bp,
    admin_bp,
    notifications_bp,
    insights_bp,
)


def create_app(config_name: str = None) -> Flask:
    if not config_name:
        if os.getenv("VERCEL") == "1" or os.getenv("VERCEL_ENV"):
            config_name = "production"
        else:
            config_name = os.getenv("FLASK_ENV", "development")

    # Static files live in public/static: Vercel serves public/ from its CDN at the
    # site root (so /static/... works), and Flask serves the same folder locally.
    # The static endpoint must always exist, otherwise url_for('static', ...) in the
    # templates raises BuildError and every page (including the error pages) fails.
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app = Flask(
        __name__,
        static_folder=os.path.join(base_dir, "public", "static"),
        static_url_path="/static",
    )
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    if config_name == "production":
        missing = [
            name for name, value in (
                ("SECRET_KEY", app.config.get("SECRET_KEY")),
                ("DATABASE_URL", app.config.get("SQLALCHEMY_DATABASE_URI")),
                ("FERNET_KEY", app.config.get("FERNET_KEY")),
            ) if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing required environment variable(s): " + ", ".join(missing)
                + ". Add them in Vercel > Project > Settings > Environment Variables and redeploy."
            )
        # Vercel terminates TLS in front of the function: trust X-Forwarded-* headers so
        # url_for, secure cookies, CSRF referrer checks and client IPs are correct.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

    # Initialize database only during local development.
    # Production database migrations and RLS policies are managed separately.
    if config_name != "production":
        init_db(app)

    # Register PostgreSQL Row Level Security transaction hooks
    with app.app_context():
        register_rls_listeners()

    # Flask-Login user loader
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Request RLS Context Synchronization
    @app.before_request
    def set_user_rls_context():
        from services.database_security import set_explicit_rls_user

        # Read the authenticated user ID without triggering Flask-Login.
        user_id = session.get("_user_id")

        if user_id:
            set_explicit_rls_user(user_id)

    @app.teardown_request
    def clear_request_rls_context(exception=None):
        from services.database_security import clear_explicit_rls_user

        clear_explicit_rls_user()

    # Notification bell data for the app shell (regular users only)
    @app.context_processor
    def inject_notifications():
        from flask_login import current_user
        from services.notification_service import NotificationService

        empty = {"nav_unread": 0, "nav_notifications": []}
        try:
            if not current_user.is_authenticated or current_user.is_admin:
                return empty
            uid = current_user.user_id
            # Generate due notifications at most every 10 minutes per session
            now_ts = int(time.time())
            if now_ts - session.get("notif_checked_at", 0) > 600:
                NotificationService.refresh(uid)
                session["notif_checked_at"] = now_ts
            return {
                "nav_unread": NotificationService.unread_count(uid),
                "nav_notifications": NotificationService.latest(uid, 5),
            }
        except Exception:
            db.session.rollback()
            return empty

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(mood_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(suggestions_bp)
    app.register_blueprint(privacy_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(insights_bp)

    # Landing Page Route (Module 1)
    @app.route("/")
    def landing():
        return render_template("index.html")

    @app.route("/favicon.ico")
    @limiter.exempt
    def favicon():
        return redirect(url_for("static", filename="img/logo.svg"), code=301)

    # Security Headers
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Content Security Policy allowing CDNs for Bootstrap, Chart.js, Lucide, Google Fonts
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self';"
        )
        response.headers["Content-Security-Policy"] = csp
        return response

    # Error Handlers
    def render_error(template, code, title):
        """Render the styled error page; never let a template problem hide the real error."""
        try:
            return render_template(template), code
        except Exception:
            app.logger.exception("Error template %s failed to render", template)
            return f"<h1>{code} &ndash; {title}</h1><p><a href='/'>Back to MindGuard</a></p>", code

    @app.errorhandler(400)
    def bad_request(e):
        return render_error("errors/400.html", 400, "Bad request")

    @app.errorhandler(401)
    def unauthorized(e):
        return render_error("errors/401.html", 401, "Unauthorized")

    @app.errorhandler(403)
    def forbidden(e):
        return render_error("errors/403.html", 403, "Forbidden")

    @app.errorhandler(404)
    def not_found(e):
        return render_error("errors/404.html", 404, "Page not found")

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_error("errors/500.html", 500, "Server error")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
