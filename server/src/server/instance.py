import multiprocessing
import threading

from dotenv import dotenv_values

# Flask App Setup
from flask import Flask
from flask_restx import Api

# load dotenv
env_config = dotenv_values(".env")  # returns a dict


app = Flask(__name__)
api = Api(app, prefix="/api/v1", title="API V1", doc="/doc", RESTX_MASK_HEADER=None)

# track active threads in the server
# key: item name, value=thread object
active_threads: dict[str, threading.Thread] = {}
active_processes: dict[str, multiprocessing.Process] = {}
