import uuid
from datetime import datetime

import structlog

server_log = structlog.getLogger("server")


def get_timestamp_from_uuid7(uuid_str: str) -> datetime:
    try:
        # Convert the UUID string to a UUID object
        uuid_obj = uuid.UUID(uuid_str)

        # UUIDv7 timestamp is stored in the first 48 bits
        timestamp_100ns = (uuid_obj.int >> 64) & ((1 << 48) - 1)

        # UUIDv7 timestamp is in 100-nanosecond intervals, so divide by 10 million to get seconds
        timestamp_seconds = timestamp_100ns / 1e7

        # Convert to a datetime object
        timestamp = datetime.utcfromtimestamp(timestamp_seconds)

        return timestamp
    except Exception as e:
        server_log.error(e)
        raise e
