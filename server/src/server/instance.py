from dotenv import dotenv_values

# load dotenv
env_config = dotenv_values(".env")  # returns a dict

# Flask App Setup
from flask import Flask
from flask_restx import Api

app = Flask(__name__)
api = Api(app)
