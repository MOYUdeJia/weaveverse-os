"""Identity shown in settings, so a stale window is obvious."""

APP_VERSION = "M14.1"


def database_revision() -> str:
    """Return the revision id that `alembic current` would print."""
    from alembic.runtime.migration import MigrationContext

    from app.db import engine

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current = context.get_current_revision()
    return current or "无"
