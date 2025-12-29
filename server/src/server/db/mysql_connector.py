import logging
import traceback
from sqlalchemy import create_engine, Column, Integer, String, Text, Time, text, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import urllib.parse
from contextlib import contextmanager

from ..instance import env_config

#!! Importing base, as re-declaring it makes it so there are 2 different bases, and create_all does not work (tables do  not get created)
from ..db.mysql_models import Implant, Listener, Base

# Logger setup
logger = logging.getLogger("server")


# defined ABOVE engine and SessionLocal module vars, so it is in scope
def get_mysql_engine() -> object | None:
    try:
        # _create_db_if_not_exist()

        host = env_config.get("MYSQL_HOST")
        user = env_config.get("MYSQL_ROOT_USER")
        password = env_config.get("MYSQL_ROOT_PASSWORD")
        database = env_config.get("MYSQL_DATABASE")

        # Check for missing configurations
        if None in (host, user, password, database):
            logger.critical(
                "Host, User, Password, or Database for MySQL is None. Check .env file, Cannot Continue"
            )
            exit()

        # SQLAlchemy connection string - using ecnoded user/pass for special character handling
        encoded_user = urllib.parse.quote_plus(user)
        encoded_password = urllib.parse.quote_plus(password)
        connection_string = (
            f"mysql+pymysql://{encoded_user}:{encoded_password}@{host}/{database}"
        )

        # Create SQLAlchemy engine
        engine = create_engine(
            connection_string, echo=False
        )  # echo=True for debug output

        # Test the connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))  # Simple query to test the connection
            logger.info(f"Connected to MySQL server as {user}@{host}.")

        return engine

    except exc.SQLAlchemyError as e:
        logger.error(f"Error connecting to MySQL: {e}\n{traceback.format_exc()}")
        return None


engine = get_mysql_engine()  # returns a single Engine instance
SessionLocal = sessionmaker(bind=engine)


def _create_db_if_not_exist():
    """
    Docstring for _create_db_if_not_exist

    Creates the c2_db in MYSQL if it does not already exist. This is the DB used for
    all the C2 operations, and it NEEDS to exist
    """

    host = env_config.get("MYSQL_HOST")
    user = env_config.get("MYSQL_ROOT_USER")
    password = env_config.get("MYSQL_ROOT_PASSWORD")
    database = env_config.get("MYSQL_DATABASE")

    # Check for missing configurations
    if None in (host, user, password, database):
        logger.critical(
            "Host, User, or Password for MySQL is None. Check .env file, Cannot Continue"
        )
        exit()

    # SQLAlchemy connection string - using ecnoded user/pass for special character handling
    encoded_user = urllib.parse.quote_plus(user)
    encoded_password = urllib.parse.quote_plus(password)

    connection_string = f"mysql+pymysql://{encoded_user}:{encoded_password}@{host}"
    engine = create_engine(connection_string, echo=False)

    with engine.connect() as conn:
        # Dynamically insert the database name into the SQL query
        create_db_sql = f"CREATE DATABASE IF NOT EXISTS {database};"

        # Execute the query
        conn.execute(text(create_db_sql))
        logger.debug(f"Database '{database}' created successfully.")


# used to get a mysql session, in context:
"""
with get_mysql_session() as session:
    ... use session
"""


@contextmanager
def get_mysql_session():
    SessionLocal = sessionmaker(bind=engine)

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f"An error occured with the MYSQL session:  {e}")
        session.rollback()
        raise
    finally:
        session.close()


def create_implants_table():
    try:
        # engine defined globally
        if engine is None:
            logger.critical("Unable to connect to MySQL. Exiting...")
            exit()

        # Debugging: Verify current schema/connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT DATABASE();"))
            db_name = result.fetchone()
            logger.debug(f"Connected to database: {db_name[0]}")

        # Create all tables in the database (if they don't exist)
        Base.metadata.create_all(engine)
        logger.debug("Table 'implants' created successfully.")

    except SQLAlchemyError as e:
        logger.error(f"Error creating table: {e}\n{traceback.format_exc()}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}\n{traceback.format_exc()}")


def mysql_setup():
    _create_db_if_not_exist()
    get_mysql_engine()
    create_implants_table()
