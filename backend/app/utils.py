from datetime import date, datetime, timezone


def utcnow() -> datetime:
    """Timezone-naive UTC timestamp (SQLite friendly)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def split_keywords(text) -> list[str]:
    if not text:
        return []
    import re
    parts = re.split(r"[,，;；、/\s]+", str(text))
    return [p.strip() for p in parts if p.strip()]


def masked(value: str | None) -> str | None:
    if not value:
        return value
    if "@" in value:
        name, domain = value.split("@", 1)
        if len(name) <= 2:
            return name[0] + "*@" + domain
        return name[:2] + "***@" + domain
    if len(value) >= 7:
        return value[:3] + "****" + value[-4:]
    return value[:1] + "***"
