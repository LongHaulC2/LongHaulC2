import argparse
import logging
from pathlib import Path

from flask import Flask

from .db.mysql_connector import mysql_setup
from .db.neo4j_connector import init_neo4j
from .db.redis_connector import get_redis_connection
from .instance import api, app, env_config
from .listeners.supervisor import restart_active_listeners
from .listeners.watchdog import start_watchdog
from .log import *
from .modules.response_pipeline.response_pipeline import start_task_batch_job

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

    parser.add_argument(
        "--no-ratelimit",
        dest="ratelimit",
        action="store_false",
        help="DISABLE rate limiting",
        default=True,
    )

    # parser.add_argument(
    #     "--debug",
    #     action="store_true",
    #     help="Enable Flask debug mode",
    # )

    return parser.parse_args()


# setup the routes
from .routes.v1.build_resource import *
from .routes.v1.implant_resource import *
from .routes.v1.listener_resource import *

logger = logging.getLogger("server")

# Test database connections
mysql_setup()
get_redis_connection()
init_neo4j()

if __name__ == "__main__":
    args = parse_args()
    if args.compression:
        from flask_compress import Compress

        server_logger.info("Response compression enabled")
        # GZIP/BR, etc compression on some flask responses
        Compress(app)
        # Some tuning
        app.config["COMPRESS_MIMETYPES"] = ["application/json"]
        app.config["COMPRESS_MIN_SIZE"] = (
            1024  # 1kb or bigger we should compress. Subject to change
        )

    if args.ratelimit:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        server_logger.info("Rate limiting enabled")
        limiter = Limiter(
            get_remote_address,
            app=app,
            # per ip rate limiting.
            # every second for implants: 3600 requests a minute. Extra 1400 for anything else. Can adjust as needed, or
            # disable with --no-ratelimit. Returns a 429 upon an ip exceeding the below threshold.
            # can oververide per func with `@limiter.limit("10/second")`
            default_limits=["5000/minute"],
        )

    start_watchdog()
    start_task_batch_job()

    # restart listeners
    restart_active_listeners()

    # temp mess with db
    # from .db.neo4j_models import Neo4jImplantNode

    # i1 = Neo4jImplantNode(implant_uuid="1234")
    # i1.save()

    # i2 = Neo4jImplantNode(implant_uuid="1235")
    # i2.save()

    # i3 = Neo4jImplantNode(implant_uuid="1236")
    # i3.save()

    # i4 = Neo4jImplantNode(implant_uuid="1237", random="")
    # i4.save()

    app.run(host="0.0.0.0", port=45045, debug=False)
