# > here, setup connector, etc. and basic neo4j stuff
"""
Neo4j planning

pip:
neomodel : orm for neo4j

#yt vid:
https://www.youtube.com/watch?v=v4CgjiVist4


Some moel notes:

- Keep things flat:

GOOD: CREATE (n: IMPLANT {implant_uuid: "00000-00000-0000-000-00", username="...")
BAD: CREATE (n: IMPLANT {implant_uuid: "00000-00000-0000-000-00", metadata:{user:...})

Planning:

misc:
 - INDEX if you MATCH on it otherwise it can get slow
 - Keep relationship direction the same, i.e. IMPLANT PARENT -> IMPLANT CHILD (important for semantics, i.e.
    LOGGED_IN_TO means parent -> child, not child -> parent)
    > left to right

Implant Node/Fields:
    UUID (unique constraint)
    *ALL* metadata
        > this scales well, its fine for all IMPLANT instances to have different properties, etc.
            scales with diff metadata

    Chaining:
        -inbox_pipe
        -outbox_pipe

Connections...

Rules: If you would ever traverse it, then make it a node & relationship

PARENT_TO and CHILD_OF for chains?

Example query:

"""

import structlog
from neo4j.exceptions import AuthError, ServiceUnavailable
from neomodel import config, db

from ..instance import env_config

# Set this at the very start of your app
logger = structlog.getLogger("server")

# config = get_config()


def ensure_fulltext_index():
    # Check if it exists
    check_query = "SHOW INDEXES YIELD name WHERE name = 'implant_search_index' RETURN count(*) > 0"
    results, _ = db.cypher_query(check_query)
    exists = results[0][0]

    if not exists:
        # Create if missing
        create_query = """
        CREATE FULLTEXT INDEX implant_search_index FOR (n:Neo4jImplantNode)
        ON EACH [
            n.implant_uuid, n.internal_ip, n.external_ip, n.system_hostname,
            n.user, n.notes, n.process, n.arch, n.pid, n.listener
        ]
        """
        db.cypher_query(create_query)


def ensure_global_fulltext_index():
    """
    Ensures a global Lucene full-text index exists across all critical C2 entities.
    This allows 'Search Everything' functionality from a single input.
    """
    index_name = "global_search_index"

    # Check if it exists
    check_query = f"SHOW INDEXES YIELD name WHERE name = '{index_name}' RETURN count(*) > 0"
    results, _ = db.cypher_query(check_query)
    exists = results[0][0]

    if not exists:
        logger.info("Creating Neo4j Full-Text Index", index=index_name)

        # We include all node labels and all potentially searchable properties.
        # Neo4j handles it gracefully if a specific node doesn't have one of these properties.
        create_query = f"""
        CREATE FULLTEXT INDEX {index_name} FOR (n:Neo4jImplantNode|Neo4jHostNode|Neo4jNetworkNode|Neo4jListenerNode|Neo4jFileNode|Neo4jNicNode)
        ON EACH [
            n.implant_uuid, n.host_uuid, n.listener_uuid, n.network_uuid, n.file_uuid,
            n.system_hostname, n.hostname, n.user, n.process, n.notes,
            n.internal_ip, n.external_ip, n.address, n.ip_address, n.cidr,
            n.file_name, n.file_path, n.protocol, n.arch
        ]
        """  # noqa
        try:
            db.cypher_query(create_query)
            logger.info("Global index created successfully.")
        except Exception as e:
            logger.error("Failed to create global index", error=e)


def init_neo4j():
    logger.info("Initializing neo4j connection")
    host = env_config.get("NEO4J_HOST")
    port = env_config.get("NEO4J_DB_PORT")
    user = env_config.get("NEO4J_USER")
    password = env_config.get("NEO4J_PASSWORD")
    # database = env_config.get("MYSQL_DATABASE")

    config.DATABASE_URL = f"bolt://{user}:{password}@{host}:{port}"
    config.NEOMODEL_CYPHER_DEBUG = 0  # shut off debug logs
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(host=host, port=port, user=user)

    if None in (host, user, port, password):
        logger.critical("Host, User, Port or Password for NEO4J is None. Check .env file, Cannot Continue")
        exit()

    if not test_neo4j_connection():
        logger.critical("Error occured with NEO4J. Exiting")
        exit()

    # setup indexs, unable to do via neomodel yet on semistructured
    ensure_fulltext_index()
    ensure_global_fulltext_index()

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
            "Connection Error: Neo4j is unreachable. Is the Docker container running? (docker container ls -a)"
        )
        return False
    except Exception as e:
        logger.critical("[-] Unknown Error occurred during connection test", error=e)
        return False
