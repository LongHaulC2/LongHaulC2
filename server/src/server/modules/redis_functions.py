from datetime import time
from sqlalchemy import exc
import logging

from ..db.mysql_models import Implant
from ..schemas.implant import ImplantUpdate, ImplantCreate

server_logger = logging.getLogger("server")

import redis
import msgpack
import uuid
from datetime import datetime
from ..instance import env_config
from ..db.redis_connector import get_redis_connection
import logging

logger = logging.getLogger("server")


class ImplantCommandService:
    """
    An interface for  command queueing/dequeueing in redis.

    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.queue_key = f"c2:implant:{self.agent_id}:tasks"

        # Initialize Redis connection
        self.redis = get_redis_connection()

    def enqueue_command(self, command: str, extra_data: dict = None) -> str:
        """Push a command to the agent's queue."""
        # PLACEHOLDER COMMAND - Structure TBD
        payload = {
            "id": str(uuid.uuid4()),
            "agent_id": self.agent_id,
            "command": command,
            "issued_at": datetime.utcnow().isoformat(),
            "extra_data": extra_data or {},
        }
        packed = msgpack.packb(payload, use_bin_type=True)
        self.redis.rpush(self.queue_key, packed)
        return payload["id"]

    def dequeue_command(self) -> dict | None:
        """Pop the next command from the agent's queue."""
        packed = self.redis.lpop(self.queue_key)
        if packed is None:
            return None
        return msgpack.unpackb(packed, raw=False)

    def peek_queue(self, n: int = 10) -> list[dict]:
        """Peek at the next n commands without removing them."""
        packed_list = self.redis.lrange(self.queue_key, 0, n - 1)
        return [msgpack.unpackb(p, raw=False) for p in packed_list]

    def queue_length(self) -> int:
        """Return the current length of the agent's queue."""
        return self.redis.llen(self.queue_key)

    def set_ttl(self, seconds: int):
        """Set an expiration on the queue key."""
        # README: Set to like 1 month by default.
        self.redis.expire(self.queue_key, seconds)
