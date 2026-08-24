"""deps.py - shared FastAPI dependencies (DB connection per request)."""

from .database import get_connection

_conn = None


def get_db():
    """A single shared connection, reused across requests - fine for a
    single-process SQLite prototype. Swapping to Azure SQL later would
    replace this with a real connection pool, without changing any
    route/service code that calls get_db()."""
    global _conn
    if _conn is None:
        _conn = get_connection()
    return _conn
