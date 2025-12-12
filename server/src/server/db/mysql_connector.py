import mysql.connector
from ..instance import env_config


def get_mysql_connection() -> object:
    user = env_config.get("MYSQL_ROOT_USER")
    password = env_config.get("MYSQL_ROOT_PASSWORD")

    mydb = mysql.connector.connect(host="localhost", user=user, password=password)
    return mydb
