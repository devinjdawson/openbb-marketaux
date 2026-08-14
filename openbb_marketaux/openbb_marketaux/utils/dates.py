"""Date helpers for the Marketaux extension."""

from datetime import datetime


def parse_datetime(value: str) -> datetime:
    """Parse a Marketaux UTC datetime string (e.g. 2024-11-08T01:24:00.000000Z)."""
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
