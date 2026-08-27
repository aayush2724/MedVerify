"""UTC ISO-8601 serialisation for API responses.

SQLite hands back naive datetimes while PostgreSQL returns timezone-aware
ones; blindly appending 'Z' to `isoformat()` produced strings like
"...+00:00Z" on PostgreSQL, which JavaScript's Date parser rejects. This
helper emits a valid UTC timestamp for either driver.
"""
from datetime import timezone


def iso_utc(dt):
    """Render a datetime as an ISO-8601 UTC string ('...Z'), or None."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat() + 'Z'
