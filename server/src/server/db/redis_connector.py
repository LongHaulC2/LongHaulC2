import redis
import logging
import traceback
from ..instance import env_config

logger = logging.getLogger("server")  # Get the logger with the same name


def get_redis_connection() -> object | None:
    try:
        host = env_config.get("REDIS_HOST")
        user = env_config.get("REDIS_USER")
        password = env_config.get("REDIS_PASSWORD")

        if None in (host, user, password):
            logger.critical(
                "Host, User, or Password for REDIS is None. Check .env file, Cannot Continue"
            )
            exit()

        logger.info(f"Connecting to REDIS server with {user}@{host}")
        r = redis.Redis(
            host=host,
            port=6379,
            decode_responses=False,  # needs to be OFF, otherwise redis tries to decode stored msgpack as utf-8, which errors out.
            username=user,
            password=password,
            # socket_connect_timeout=5, #timeouts are 10 seconds by default
            # socket_timeout=5,
        )

        try:
            # Send a PING command to Redis to verify the connection
            response = r.ping()
            if response:
                logger.info(f"REDIS connection is alive")
            else:
                logger.info(f"REDIS connection is not alive")

        except redis.ConnectionError as e:
            logger.warning(f"Failed to connect to REDIS: {e}")

        return r

    except Exception as e:
        logger.error(f"Error connecting to REDIS: {e}\n{traceback.format_exc()}")
        return None
