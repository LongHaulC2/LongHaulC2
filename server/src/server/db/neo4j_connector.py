# > here, setup connector, etc. and basic neo4j stuff
"""
Neo4j planning

pip:
neomodel : orm for neo4j

#yt vid:
https://www.youtube.com/watch?v=v4CgjiVist4
"""
import logging

import structlog
from neo4j.exceptions import AuthError, ServiceUnavailable
from neomodel import config, db

from ..instance import env_config

# Set this at the very start of your app
logger = logging.getLogger("server")


def init_neo4j():
    logger.info("Initializing neo4j connection")
    host = env_config.get("NEO4J_HOST")
    port = env_config.get("NEO4J_DB_PORT")
    user = env_config.get("NEO4J_USER")
    password = env_config.get("NEO4J_PASSWORD")
    # database = env_config.get("MYSQL_DATABASE")

    config.DATABASE_URL = f"bolt://{user}:{password}@{host}:{port}"

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(host=host, port=port, user=user)

    if not test_neo4j_connection():
        logger.critical("Error occured with NEO4J. Exiting")
        exit()

    # clear vars after this
    structlog.contextvars.clear_contextvars()


def test_neo4j_connection():
    logger.info("Testing Neo4j graph database connection")
    try:
        db.cypher_query("RETURN 1")
        logger.info("NEO4J database is online and reachable.")
        return True

    except AuthError:
        logger.critical("Auth Error: Invalid Neo4j credentials.")
        return False
    except ServiceUnavailable:
        logger.critical(
            "Connection Error: Neo4j is unreachable. Is the Docker container running on port 7687? (docker container ls -a)"
        )
        return False
    except Exception as e:
        logger.critical(f"[-] Unknown Error occurred during connection test: {e}")
        return False
