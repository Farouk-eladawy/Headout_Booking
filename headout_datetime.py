"""
Convert Headout trip date/time (Cairo wall-clock) to Airtable UTC ISO.

Airtable stores datetimes in UTC and displays them in the field timezone
(EEST/EET for Cairo). Headout prints the experience time in local Egypt time,
so we must attach Africa/Cairo (DST-aware) and then convert to UTC.

A hardcoded -2h offset is only correct in winter (EET, UTC+2) and shows the
trip two hours early in summer (EEST, UTC+3).
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo

    CAIRO_TZ = ZoneInfo("Africa/Cairo")
    # Fail fast on Windows if tzdata is missing/incomplete.
    _ = datetime(2026, 8, 14, 20, 0, tzinfo=CAIRO_TZ).utcoffset()
except Exception:  # pragma: no cover - Windows without tzdata
    CAIRO_TZ = None

UTC_TZ = timezone.utc


def _last_weekday(year: int, month: int, weekday: int) -> datetime:
    """Last given weekday in a month. Monday=0 ... Sunday=6."""
    if month == 12:
        nxt = datetime(year + 1, 1, 1)
    else:
        nxt = datetime(year, month + 1, 1)
    cursor = nxt - timedelta(days=1)
    while cursor.weekday() != weekday:
        cursor -= timedelta(days=1)
    return cursor.replace(hour=0, minute=0, second=0, microsecond=0)


def _egypt_dst_offset(dt: datetime) -> timedelta:
    """
    Egypt DST fallback when IANA tzdata is unavailable.
    DST: last Friday of April 00:00 through last Thursday of October 24:00.
    """
    year = dt.year
    start = _last_weekday(year, 4, 4)  # Friday
    end = _last_weekday(year, 10, 3) + timedelta(days=1)  # Friday 00:00 after last Thursday
    naive = dt.replace(tzinfo=None)
    if start <= naive < end:
        return timedelta(hours=3)
    return timedelta(hours=2)


def _parse_headout_datetime(date_str: str, time_str: Optional[str] = None) -> datetime:
    text = (date_str or "").strip()
    if not text:
        raise ValueError("empty date")

    extra = (time_str or "").strip()
    if extra:
        text = f"{text} {extra}"

    # Drop any timezone the source attached. Headout times are Cairo wall-clock;
    # AI/ISO often incorrectly tags them as Z/UTC or a fixed +02:00 offset.
    cleaned = re.sub(r"[Zz]$", "", text.strip())
    cleaned = re.sub(r"[+-]\d{2}:?\d{2}$", "", cleaned).strip()

    try:
        from dateutil import parser as date_parser

        dt = date_parser.parse(cleaned, fuzzy=True, ignoretz=True)
    except Exception:
        dt = None
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%b %d, %Y %I:%M %p",
            "%B %d, %Y %I:%M %p",
            "%b %d, %Y %H:%M",
            "%Y-%m-%d",
            "%b %d, %Y",
            "%B %d, %Y",
        ):
            try:
                dt = datetime.strptime(cleaned, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            raise ValueError(f"unparseable datetime: {date_str!r} {time_str!r}")

    return dt.replace(tzinfo=None)


def cairo_local_to_airtable_iso(date_str: str, time_str: Optional[str] = None) -> Optional[str]:
    """
    Interpret date/time as Africa/Cairo local time and return UTC ISO for Airtable.

    Example (summer): Aug 14, 2026 08:00 PM Cairo -> 2026-08-14T17:00:00.000Z
    Airtable then displays 08:00 PM / 20:00 EEST.
    """
    if not date_str:
        return None

    dt = _parse_headout_datetime(str(date_str), time_str)

    if CAIRO_TZ is not None:
        aware = dt.replace(tzinfo=CAIRO_TZ)
        utc_dt = aware.astimezone(UTC_TZ)
    else:
        utc_dt = dt - _egypt_dst_offset(dt)
        utc_dt = utc_dt.replace(tzinfo=UTC_TZ)

    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
