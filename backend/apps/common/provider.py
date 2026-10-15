from collections.abc import Iterable
from datetime import datetime
from datetime import timezone as dt_timezone
from urllib.parse import parse_qs, urlparse

from django.utils import timezone
from django.utils.dateparse import parse_datetime


def as_dict(value):
    return value if isinstance(value, dict) else {}


def as_list(value):
    return value if isinstance(value, list) else []


def as_iterable(value):
    """Accept client iterators while rejecting JSON objects and primitives."""
    if isinstance(value, (str, bytes, dict)) or not isinstance(value, Iterable):
        return ()
    return value


def provider_id(value):
    """Return a usable provider identity without manufacturing one."""
    return value if isinstance(value, str) and value.strip() else None


def safe_text(value):
    return value if isinstance(value, str) else ""


def safe_count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def safe_bool(value, *, default):
    return value if isinstance(value, bool) else default


def provider_time(value, *, milliseconds=False) -> datetime | None:
    """Parse provider time without inventing a receipt time or an unknown timezone.

    Messenger webhooks use numeric milliseconds; Graph history uses offset-bearing
    ISO timestamps. Invalid dates, bools, non-finite and overflowing numbers fail
    explicitly. Future-time authorization policy belongs to the inbox domain.
    """
    try:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            seconds = value / 1000 if milliseconds else value
            return datetime.fromtimestamp(seconds, tz=dt_timezone.utc)
        if milliseconds:
            return None
        parsed = (
            value
            if isinstance(value, datetime)
            else (parse_datetime(value) if isinstance(value, str) else None)
        )
        if parsed is None or timezone.is_naive(parsed):
            return None
        return parsed.astimezone(dt_timezone.utc)
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def safe_url(value):
    if not isinstance(value, str):
        return ""
    parsed = urlparse(value)
    if parsed.scheme != "https" or any("token" in key.lower() for key in parse_qs(parsed.query)):
        return ""
    return value


def media_items(attachments):
    result = []
    items = (
        as_list(as_dict(attachments).get("data"))
        if isinstance(attachments, dict)
        else as_list(attachments)
    )
    for raw_item in items:
        item = as_dict(raw_item)
        media = as_dict(item.get("media"))
        image = as_dict(media.get("image")).get("src", "")
        payload = as_dict(item.get("payload"))
        image_data = as_dict(item.get("image_data"))
        url = safe_url(
            image
            or payload.get("url")
            or item.get("file_url")
            or image_data.get("url")
            or item.get("url", "")
        )
        if url:
            result.append({"type": safe_text(item.get("type")) or "attachment", "url": url})
    return result
