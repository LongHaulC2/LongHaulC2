import logging
from pathlib import Path

from .instance import env_config, app, api
from .db.mysql_connector import mysql_setup
from .db.redis_connector import get_redis_connection
from .log import *

# setup the routes
from .routes.v1.hello_resource import *


logger = logging.getLogger("server")

# Test database connections
mysql_setup()
get_redis_connection()

app.run(host="0.0.0.0", port=45045, debug=False)
