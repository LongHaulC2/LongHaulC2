import mysql.connector
from ..instance import env_config


def get_mysql_connection() -> object:
    host = env_config.get("MYSQL_HOST")
    user = env_config.get("MYSQL_ROOT_USER")
    password = env_config.get("MYSQL_ROOT_PASSWORD")

    mydb = mysql.connector.connect(host=host, user=user, password=password)
    return mydb
