import logging
from pathlib import Path
from flask import Flask
from flask_compress import Compress
import argparse
from .instance import env_config, app, api
from .db.mysql_connector import mysql_setup
from .db.redis_connector import get_redis_connection
from .log import *

server_logger = logging.getLogger("server")
api_logger = logging.getLogger("api")


def parse_args():
    parser = argparse.ArgumentParser(description="Flask API Server")

    # parser.add_argument(
    #     "--host",
    #     default="0.0.0.0",
    #     help="Host to bind (default: 0.0.0.0)",
    # )

    # parser.add_argument(
    #     "--port",
    #     type=int,
    #     default=45045,
    #     help="Port to bind (default: 45045)",
    # )

    parser.add_argument(
        "--no-compression",
        dest="compression",
        action="store_false",
        help="DISABLE HTTP response compression. ",
        default=True,
    )

    # parser.add_argument(
    #     "--debug",
    #     action="store_true",
    #     help="Enable Flask debug mode",
    # )

    return parser.parse_args()


# setup the routes
from .routes.v1.hello_resource import *
from .routes.v1.implant_resource import *


logger = logging.getLogger("server")

# Test database connections
mysql_setup()
get_redis_connection()


if __name__ == "__main__":
    args = parse_args()
    if args.compression:
        api_logger.info("Response compression enabled")
        # GZIP/BR, etc compression on some flask responses
        Compress(app)
        # Some tuning
        app.config["COMPRESS_MIMETYPES"] = ["application/json"]
        app.config["COMPRESS_MIN_SIZE"] = (
            1024  # 1kb or bigger we should compress. Subject to change
        )

    app.run(host="0.0.0.0", port=45045, debug=False)
