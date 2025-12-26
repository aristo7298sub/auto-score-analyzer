from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return a timezone-aware UTC datetime.

    We store timestamps in Postgres with timezone and compare them in Python.
    Using naive datetimes (datetime.utcnow()) will raise TypeError when compared
    against timezone-aware values returned by SQLAlchemy.
    """

    return datetime.now(timezone.utc)
