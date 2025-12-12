import mysql.connector
from ..instance import env_config
import logging
import traceback

logger = logging.getLogger("server")


def get_mysql_connection() -> object | None:
    try:
        host = env_config.get("MYSQL_HOST")
        user = env_config.get("MYSQL_ROOT_USER")
        password = env_config.get("MYSQL_ROOT_PASSWORD")

        if None in (host, user, password):
            logger.critical(
                "Host, User, or Password for MYSQL is None. Check .env file, Cannot Continue"
            )
            exit()

        logger.info(f"Connecting to MYSQL server with {user}@{host}")
        mydb = mysql.connector.connect(host=host, user=user, password=password)
        return mydb

    except Exception as e:
        logger.error(f"Error connecting to MySQL: {e}\n{traceback.format_exc()}")
        return None
