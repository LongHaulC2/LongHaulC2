import uuid
from datetime import UTC, datetime

import structlog

server_log = structlog.getLogger("server")


def get_timestamp_from_uuid7(uuid_str: str) -> datetime:
    try:
        uuid_obj = uuid.UUID(uuid_str)

        # Shift right by 80 bits to isolate the top 48 bits
        timestamp_ms = uuid_obj.int >> 80

        # UUIDv7 is in milliseconds, so divide by 1000 for seconds
        timestamp_seconds = timestamp_ms / 1000.0

        # Return a fully timezone-aware UTC datetime object
        return datetime.fromtimestamp(timestamp_seconds, tz=UTC)

    except Exception as e:
        server_log.error(e)
        raise e


def get_time_ago(target_timestamp: datetime) -> str:
    """Returns a granular 'X days, Y hours, Z minutes ago' string."""
    now_utc = datetime.now(UTC)
    delta = now_utc - target_timestamp

    # Extract the core components
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60

    # Build the string dynamically
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    # Catch cases where the implant *just* registered (under 60 seconds)
    if not parts:
        return "just now"

    return ", ".join(parts) + " ago"
