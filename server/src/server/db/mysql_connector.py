import base64
import json
import urllib.parse
from contextlib import contextmanager

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

#!! Importing base, as re-declaring it in diff py files makes it so there are different bases, and create_all
# does not work (tables do not get created)
from ..db.mysql_models import Base
from ..instance import env_config

# Logger setup
logger = structlog.getLogger("server")


# = Serializer for bytes ======================================
# Add a serializer for bytes, so they are stored as base64 in db. this is needed for storing task responses,
# which can commonly have binary data (ex: file download response).


# This also makes it easier on clients/api, to get this data as base64 string, rather than raw bytes.
class BytesEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            logger.debug("Encoding bytes to base64 string for JSON serialization in MySQL")
            return base64.b64encode(o).decode(
                "ascii"
            )  # ascii cuz A-Z, a-z, digits, +, /, = only, so no risk of decode issues.
        return super().default(o)


def json_serializer(obj):
    return json.dumps(obj, cls=BytesEncoder)


# ============================================================

engine = None
SessionLocal = None


def _get_db_connection_params():
    """Helper to extract and format database credentials from environment."""
    host = env_config.get("MYSQL_HOST")
    port = env_config.get("MYSQL_PORT")
    user = env_config.get("MYSQL_ROOT_USER")
    password = env_config.get("MYSQL_ROOT_PASSWORD")
    database = env_config.get("MYSQL_DATABASE")

    if None in (host, port, user, password, database):
        logger.critical("Database configuration is missing in .env file. Cannot continue.")
        exit()

    encoded_user = urllib.parse.quote_plus(user)
    encoded_password = urllib.parse.quote_plus(password)

    return host, port, encoded_user, encoded_password, database


def _create_db_if_not_exist(host, port, user, password, database):
    """Connects to the MySQL instance (without a DB name) to create the schema."""
    # Note: No database name at the end of this string, otherwise it'll try to connect to a db that doesn't exist
    base_conn_str = f"mysql+pymysql://{user}:{password}@{host}:{port}"

    # Use a temporary engine that doesn't care about the specific DB
    temp_engine = create_engine(base_conn_str)
    try:
        with temp_engine.connect() as conn:
            # can probably inject this, but it's specified in the makefile so it's "trusted" input
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {database}"))
            logger.debug("Ensured database exists.", database=database)
    finally:
        temp_engine.dispose()  # Clean up the temp connection immediately


def mysql_setup():
    global engine, SessionLocal

    host, port, user, password, database = _get_db_connection_params()

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(host=host, port=port, user=user, database=database)

    _create_db_if_not_exist(host, port, user, password, database)

    conn_str = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

    try:
        engine = create_engine(conn_str, echo=False, json_serializer=json_serializer)

        # Test it immediately
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            result = conn.execute(text("SELECT DATABASE();"))
            db_name = result.fetchone()
            if db_name:
                logger.debug("Connected to database", database_name=db_name[0])
            else:
                logger.warning("Could not get name of the database")

        SessionLocal = sessionmaker(bind=engine)
        logger.info("Main MySQL engine initialized successfully.")

        # Create all tables in the database (if they don't exist)
        Base.metadata.create_all(engine)
        logger.debug("Table 'implants' created successfully.")

    except SQLAlchemyError as e:
        logger.critical("Database setup failed", error=e)
        engine = None
    except Exception as e:
        logger.critical("Unexpected error during setup", error=e)
        engine = None
    finally:
        # clear out any extra vars set after init
        structlog.contextvars.clear_contextvars()


# used to get a mysql session, in context:
"""
with get_mysql_session() as session:
    ... use session
"""


@contextmanager
def get_mysql_session():
    if engine is None or SessionLocal is None:
        raise Exception("Database engine not initialized. Ensure mysql_setup() ran successfully before querying.")

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error("An error occurred with the MYSQL session", error=e)
        session.rollback()
        raise
    finally:
        session.close()
