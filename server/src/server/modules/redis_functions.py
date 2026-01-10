import logging
from dataclasses import asdict

from ..schemas.implant import Task

server_logger = logging.getLogger("server")

import logging

import msgpack

from ..db.redis_connector import get_redis_connection


class RedisImplantTaskService:
    """
    An interface for task queueing/dequeueing in redis.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.outbox_key = f"c2:implant:{self.agent_id}:tasks:outbox"
        self.inbox_key = f"c2:implant:{self.agent_id}:tasks:inbox"
        self.redis = get_redis_connection()

    def enqueue_task(self, task: Task):
        """Covnerts task to msgpack, then push said task to the agent's queue.

        Takes a dataclass of Task
        """
        try:
            # get datatclass, convert to dict
            # using as dict as we have a nested dataclass (TaskData), rather than vars(task)
            payload = asdict(task)
            server_logger.debug(f"Adding task to queue: {payload}")
            packed = msgpack.packb(payload, use_bin_type=True)
            self.redis.rpush(self.outbox_key, packed)

        except Exception as e:
            server_logger.error(e)
            raise e

    def clear_queue(self) -> int:
        """Clear all tasks but keep the key. Returns the number of tasks removed (approx)."""
        # Get current length (optional)
        queue_length = self.redis.llen(self.outbox_key)

        # Trim to empty
        self.redis.ltrim(self.outbox_key, 1, 0)

        return queue_length

    # ---------- Response funcs ----------

    def enqueue_response(self, implant_response: bytes):
        """Push a response to the inbox of the client."""
        try:
            self.redis.rpush(self.inbox_key, implant_response)
        except Exception as e:
            server_logger.error(e)
            raise e

    def dequeue_response(self) -> bytes | None:
        """Pop the next task (MessagePack bytes)."""
        return self.redis.lpop(self.inbox_key)

    def dequeue_response_dict(self) -> dict | None:
        """Pop and dequue the next response."""
        packed = self.dequeue_response()
        if packed is None:
            return None
        return msgpack.unpackb(packed, raw=False)

    def clear_response_queue(self) -> int:
        """Clear all responses but keep the key. Returns the number of responses removed (approx)."""
        # Get current length (optional)
        queue_length = self.redis.llen(self.inbox_key)

        # Trim to empty
        self.redis.ltrim(self.inbox_key, 1, 0)

        return queue_length

    def response_queue_length(self) -> int:
        return self.redis.llen(self.inbox_key)

    # ---------- RAW (bytes) ----------

    def dequeue_task(self) -> bytes | None:
        """Pop the next task (MessagePack bytes)."""
        return self.redis.lpop(self.outbox_key)

    def peek_queue(self, n: int = 10) -> list[bytes]:
        """Peek at the next n tasks (MessagePack bytes)."""
        return self.redis.lrange(self.outbox_key, 0, n - 1)

    def queue_length(self) -> int:
        return self.redis.llen(self.outbox_key)

    def set_ttl(self, seconds: int):
        self.redis.expire(self.outbox_key, seconds)

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
