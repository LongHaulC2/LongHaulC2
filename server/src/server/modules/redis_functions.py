from datetime import time
from sqlalchemy import exc
import logging
from dataclasses import asdict

from ..db.mysql_models import Implant
from ..schemas.implant import ImplantUpdate, ImplantCreate, Task

server_logger = logging.getLogger("server")

import redis
import msgpack
import uuid
from datetime import datetime
from ..instance import env_config
from ..db.redis_connector import get_redis_connection
import logging


class ImplantTaskService:
    """
    An interface for task queueing/dequeueing in redis.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.queue_key = f"c2:implant:{self.agent_id}:tasks"
        self.redis = get_redis_connection()

    def enqueue_task(self, task: Task) -> str:
        """Push a task to the agent's queue.

        Takes a dataclass of Task
        """
        # get datatclass, convert to dict
        # using as dict as we have a nested dataclass (TaskData), rather than vars(task)
        payload = asdict(task)
        server_logger.debug(f"Adding task to queue: {payload}")
        packed = msgpack.packb(payload, use_bin_type=True)
        self.redis.rpush(self.queue_key, packed)
        return payload["id"]

    # ---------- RAW (bytes) ----------

    def dequeue_task(self) -> bytes | None:
        """Pop the next task (MessagePack bytes)."""
        return self.redis.lpop(self.queue_key)

    def peek_queue(self, n: int = 10) -> list[bytes]:
        """Peek at the next n tasks (MessagePack bytes)."""
        return self.redis.lrange(self.queue_key, 0, n - 1)

    def queue_length(self) -> int:
        return self.redis.llen(self.queue_key)

    def set_ttl(self, seconds: int):
        self.redis.expire(self.queue_key, seconds)

    # ---------- DECODED (dict) ----------
    # Some extra function to  return tasks as a dict, for various reasons/compatability
    # These are the exceptions, not the standard

    def dequeue_task_dict(self) -> dict | None:
        """Pop and decode the next task."""
        packed = self.dequeue_task()
        if packed is None:
            return None
        return msgpack.unpackb(packed, raw=False)

    def peek_queue_dict(self, n: int = 10) -> list[dict]:
        """Peek and decode the next n tasks."""
        return [msgpack.unpackb(p, raw=False) for p in self.peek_queue(n)]
