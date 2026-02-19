import logging
import traceback

import redis

from ..instance import env_config

logger = logging.getLogger("server")  # Get the logger with the same name
import structlog

# flag for not printing connection logs after the first connect
_shut_the_f_up_after_first_connect = False


def get_redis_connection() -> object | None:
    global _shut_the_f_up_after_first_connect
    try:
        host = env_config.get("REDIS_HOST")
        user = env_config.get("REDIS_USER")
        port = env_config.get("REDIS_PORT")
        password = env_config.get("REDIS_PASSWORD")

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(host=host, port=port, user=user)

        if None in (host, user, password):
            logger.critical(
                "Host, User, or Password for REDIS is None. Check .env file, Cannot Continue"
            )
            exit()

        if not _shut_the_f_up_after_first_connect:
            logger.info(f"Connecting to REDIS server")

        r = redis.Redis(
            host=host,
            port=port,
            decode_responses=False,  # needs to be OFF, otherwise redis tries to decode stored msgpack as utf-8, which errors out.
            username=user,
            password=password,
            # socket_connect_timeout=5, #timeouts are 10 seconds by default
            # socket_timeout=5,
        )

        # quick connection test
        try:
            if r.ping():
                if not _shut_the_f_up_after_first_connect:
                    logger.info("REDIS connection is alive")
                    _shut_the_f_up_after_first_connect = True
        except redis.ConnectionError as e:
            logger.warning(f"Failed to connect to REDIS: {e}")

        # clear structlog
        structlog.contextvars.clear_contextvars()

        return r

    except Exception as e:
        logger.error(f"Error connecting to REDIS: {e}\n{traceback.format_exc()}")
        structlog.contextvars.clear_contextvars()
        return None
