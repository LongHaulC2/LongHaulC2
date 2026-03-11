import multiprocessing
import threading

from dotenv import dotenv_values

# Flask App Setup
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_restx import Api

# load dotenv
env_config = dotenv_values(".env")  # returns a dict


app = Flask(__name__)

# config options

# get rid of mask field in swagger
app.config["RESTX_MASK_SWAGGER"] = False
app.config["RESTX_VALIDATE"] = True

jwt_key = env_config.get("JWT_SECRET_KEY")
if not jwt_key:
    raise ValueError("CRITICAL: JWT_SECRET_KEY is missing from the .env file or the file was not found!")

app.config["JWT_SECRET_KEY"] = jwt_key

# then setup objects
jwt = JWTManager(app)
api = Api(app, prefix="/api/v1", title="API V1", doc="/doc")

# track active threads in the server
# key: item name, value=thread object
active_threads: dict[str, threading.Thread] = {}
active_processes: dict[str, multiprocessing.Process] = {}
