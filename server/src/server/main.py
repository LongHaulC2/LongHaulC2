from flask import Flask
from flask_restx import Api
import logging
from pathlib import Path

from .instance import env_config
from .db.mysql_connector import get_mysql_connection

# Define log directory
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
# Setup Loggers
log_file = Path(log_dir) / "server.log"
logger = logging.getLogger("server")  # server logger for all server actions
logging.basicConfig(filename=log_file, encoding="utf-8", level=logging.DEBUG)
logger.info("Server Startup")


print(get_mysql_connection)

app = Flask(__name__)
api = Api(app)
