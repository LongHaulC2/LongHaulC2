import argparse
import sys

import structlog

# extensions, noqa403 as this sets up a handler on import
from .api_extensions.orjson_override import *  # noqa F403
from .db.mysql_connector import get_mysql_session, mysql_setup
from .db.mysql_functions import MySQLUserService
from .db.neo4j_connector import init_neo4j
from .db.redis_connector import get_redis_connection
from .instance import app, env_config
from .listeners.supervisor import restart_active_listeners
from .listeners.watchdog import start_watchdog

# our loggers, need to import this so the loggers get imported & setup in main (at start), otherwise they are
# init'd when imported in other locations
from .log import *  # noqa F403
from .modules.response_pipeline.response_pipeline import start_task_batch_job

server_logger = structlog.getLogger("server")
api_logger = structlog.getLogger("api")


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
# noqa 403 as this is how these need to be imported for flask-restx
# noqa 402 as these need to be imported here, rather than earlier
# last, explicitly setup errors
from .api_extensions.error_definitions import *  # noqa: F403, E402
from .routes.v1.auth_resource import *  # noqa: F403, E402
from .routes.v1.build_resource import *  # noqa: F403, E402
from .routes.v1.filestore_resource import *  # noqa: F403, E402
from .routes.v1.graph_resource import *  # noqa: F403, E402
from .routes.v1.health_resource import *  # noqa: F403, E402
from .routes.v1.implant_resource import *  # noqa: F403, E402
from .routes.v1.listener_resource import *  # noqa: F403, E402

logger = structlog.getLogger("server")

# Test database connections
mysql_setup()
get_redis_connection()
init_neo4j()


def initialize_app(compression=True, ratelimit=True):
    if compression:
        from flask_compress import Compress

        server_logger.info("Response compression enabled")
        # GZIP/BR, etc compression on some flask responses
        Compress(app)
        # Some tuning
        app.config["COMPRESS_MIMETYPES"] = ["application/json"]
        app.config["COMPRESS_MIN_SIZE"] = 1024  # 1kb or bigger we should compress. Subject to change

    if ratelimit:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        server_logger.info("Rate limiting enabled")
        limiter = Limiter(  # noqa
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

    # register API user if no other users
    with get_mysql_session() as session:
        msus = MySQLUserService(session)
        msus.create_initial_user(username=env_config.get("INIT_API_USER"), password=env_config.get("INIT_API_PASS"))


# gunicorn
def run_api_with_gunicorn():
    """
    Dedicated entry point for Gunicorn.
    Gunicorn will call this function to get the Flask app instance.

    Returns an app instance
    """
    server_logger.info("Starting in Production Mode (Gunicorn)")

    initialize_app(compression=True, ratelimit=True)

    return app


def run_api_dev_server():
    """Dedicated entry point for local development.

    Does not return an app instance, just runs the dev server
    """
    server_logger.info("Starting in Development Mode")
    args = parse_args()

    initialize_app(compression=args.compression, ratelimit=args.ratelimit)

    app.run(host="0.0.0.0", port=45045, debug=False)


if __name__ == "__main__":
    try:
        run_api_dev_server()
    except KeyboardInterrupt:
        server_logger.info("Server shutdown requested via KeyboardInterrupt")
        sys.exit(0)
