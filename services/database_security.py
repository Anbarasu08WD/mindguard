
import logging

from extensions import db

logger = logging.getLogger(__name__)


def set_rls_context(session, transaction, connection):
    """
    Set a transaction-local PostgreSQL user identity.

    Never access Flask-Login's current_user inside this event:
    it can cause recursive user loading while the login user
    is being retrieved from the database.
    """
    user_id = session.info.get("app_user_id")
    user_id_str = str(user_id) if user_id is not None else ""

    connection.exec_driver_sql(
        "SELECT set_config('app.current_user_id', %s, true)",
        (user_id_str,)
    )


def register_rls_listeners():
    """Register the SQLAlchemy transaction-start listener."""
    from sqlalchemy import event

    if not event.contains(db.session, "after_begin", set_rls_context):
        event.listen(db.session, "after_begin", set_rls_context)


def set_explicit_rls_user(user_id: int | str) -> None:
    """
    Set the authenticated user's identity for the current transaction.
    """
    if user_id is None:
        raise ValueError("An authenticated user ID is required.")

    uid_str = str(user_id)

    if not uid_str:
        raise ValueError("The authenticated user ID cannot be empty.")

    db.session.info["app_user_id"] = uid_str

    # This also handles a transaction that started earlier while
    # Flask-Login was loading the user.
    db.session.connection().exec_driver_sql(
        "SELECT set_config('app.current_user_id', %s, true)",
        (uid_str,)
    )


def clear_explicit_rls_user() -> None:
    """
    Remove the explicit identity from the current SQLAlchemy session.

    The transaction-local PostgreSQL setting resets automatically
    when its transaction ends. Avoid opening a new connection here.
    """
    db.session.info.pop("app_user_id", None)
