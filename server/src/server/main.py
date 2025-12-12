from flask import Flask
from flask_restx import Api
from .instance import env_config
from .db.mysql_connector import get_mysql_connection

print(get_mysql_connection)

app = Flask(__name__)
api = Api(app)
