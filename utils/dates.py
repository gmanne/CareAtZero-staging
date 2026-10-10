"""
The app's idea of "today".

Pop-up events are shown only until their end date, and the Care Access Score
counts the days until an event, so the app needs the real current date.
It uses North Carolina's time zone (the pilot area), so "today" doesn't flip
early in the evening on servers that run on UTC time.

For tests or a repeatable demo, set the CAREATZERO_TODAY environment variable
to a fixed date, e.g.  CAREATZERO_TODAY=2026-09-16
"""
import datetime
import os

try:
    from zoneinfo import ZoneInfo
    APP_TIMEZONE = ZoneInfo("America/New_York")
except Exception:  # no time zone database available (e.g. Windows without tzdata)
    APP_TIMEZONE = None


def today() -> datetime.date:
    """Today's date in the app's time zone, or the CAREATZERO_TODAY override."""
    override = os.environ.get("CAREATZERO_TODAY", "").strip()
    if override:
        try:
            return datetime.date.fromisoformat(override)
        except ValueError:
            pass  # ignore a badly formatted override and use the real date
    if APP_TIMEZONE is not None:
        return datetime.datetime.now(APP_TIMEZONE).date()
    return datetime.date.today()


def today_str() -> str:
    """Today's date as YYYY-MM-DD, the format the database uses."""
    return today().isoformat()


def format_checked_date(value) -> str:
    """'2026-09-16' -> 'Sep 16, 2026' for display; anything else is shown as-is."""
    try:
        return datetime.date.fromisoformat(str(value)[:10]).strftime("%b %d, %Y").replace(" 0", " ")
    except (TypeError, ValueError):
        return str(value) if value else "date not listed"


def format_event_dates(start, end=None) -> str:
    """'2027-04-24', '2027-04-25' -> 'Apr 24–25, 2027'; one day -> 'Apr 24, 2027'."""
    try:
        d1 = datetime.date.fromisoformat(str(start)[:10])
        d2 = datetime.date.fromisoformat(str(end)[:10]) if end else d1
    except (TypeError, ValueError):
        return str(start or "Date to be announced")
    if d2 <= d1:
        return f"{d1:%b} {d1.day}, {d1.year}"
    if (d1.year, d1.month) == (d2.year, d2.month):
        return f"{d1:%b} {d1.day}–{d2.day}, {d1.year}"
    if d1.year == d2.year:
        return f"{d1:%b} {d1.day} – {d2:%b} {d2.day}, {d1.year}"
    return f"{d1:%b} {d1.day}, {d1.year} – {d2:%b} {d2.day}, {d2.year}"
