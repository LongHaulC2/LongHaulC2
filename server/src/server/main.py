import logging
from pathlib import Path
from flask import Flask
from flask_restx import Api
from .instance import env_config
from .db.mysql_connector import mysql_setup
from .db.redis_connector import get_redis_connection
from .log import *

logger = logging.getLogger("server")

# Test database connections
mysql_setup()
get_redis_connection()

# Flask App Setup
app = Flask(__name__)
api = Api(app)
