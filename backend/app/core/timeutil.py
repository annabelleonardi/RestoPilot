"""Store-local time helpers.

Sales KPIs must bucket by the store's business day (Asia/Jakarta, UTC+7):
a naive ``datetime.now()`` puts a 20:00 WIB sale on the wrong UTC day.

Storage convention: timestamps are written as **naive UTC** (SQLite drops
offsets on bind, so aware objects would lose their meaning in storage).
Every writer normalizes through ``to_utc_naive``; readers convert back to
the store's local calendar with ``to_store_date``.
"""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

DEFAULT_TZ = "Asia/Jakarta"


def store_tz(store) -> ZoneInfo:
    return ZoneInfo(getattr(store, "timezone", None) or DEFAULT_TZ)


def store_now(store) -> datetime:
    """Current instant expressed in the store's local time (aware)."""
    return datetime.now(store_tz(store))


def to_utc(dt: datetime) -> datetime:
    """Normalize any datetime to timezone-aware UTC. Naive input is assumed UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_utc_naive(dt: datetime) -> datetime:
    """Normalize any datetime to the naive-UTC storage convention."""
    return to_utc(dt).replace(tzinfo=None)


def store_day_start_utc(store, local_date: date) -> datetime:
    """Midnight at the store's local day, expressed as aware UTC (query bound)."""
    tz = store_tz(store)
    return datetime(local_date.year, local_date.month, local_date.day, tzinfo=tz).astimezone(
        timezone.utc
    )


def to_store_date(store, dt: datetime) -> date:
    """The store-local calendar day an (aware UTC) timestamp falls on."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(store_tz(store)).date()
