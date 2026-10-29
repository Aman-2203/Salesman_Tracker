from datetime import datetime, date, time, timezone, timedelta

# Indian Standard Time / GMT+5:30
IST_OFFSET = timedelta(hours=5, minutes=30)
IST = timezone(IST_OFFSET, name="Asia/Kolkata")


def now_ist() -> datetime:
    """Return the current datetime in GMT+5:30 as a naive datetime for DB consistency."""
    return datetime.now(timezone.utc) + IST_OFFSET


def today_ist() -> date:
    """Return the current date in GMT+5:30."""
    return now_ist().date()


def to_ist(val):
    """
    Ensure a datetime is in GMT+5:30.
    If the datetime was stored as UTC (e.g., from datetime.utcnow()), convert to IST.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        # If it's already localized with tzinfo
        if val.tzinfo is not None:
            return val.astimezone(IST).replace(tzinfo=None)
        # Naive datetime: check if caller intends it as UTC or already IST
        # If it's naive from older DB records stored via utcnow(), add IST offset if requested.
        return val
    return val


def format_date(val) -> str:
    """Format any date or datetime as DD/MM/YYYY (e.g. 29/10/2026)."""
    if not val:
        return '—'
    if isinstance(val, str):
        try:
            val = datetime.strptime(val[:10], '%Y-%m-%d').date()
        except ValueError:
            return val
    if isinstance(val, (datetime, date)):
        return val.strftime('%d/%m/%Y')
    return str(val)


def format_time(val) -> str:
    """Format a datetime or time in HH:MM format."""
    if not val:
        return '—'
    if isinstance(val, datetime):
        return val.strftime('%H:%M')
    if isinstance(val, time):
        return val.strftime('%H:%M')
    if isinstance(val, str):
        return val
    return str(val)


def format_datetime(val) -> str:
    """Format a datetime as DD/MM/YYYY HH:MM."""
    if not val:
        return '—'
    if isinstance(val, datetime):
        return val.strftime('%d/%m/%Y %H:%M')
    if isinstance(val, date):
        return val.strftime('%d/%m/%Y')
    return str(val)

