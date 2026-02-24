import orjson
import structlog
from flask import make_response

from ..instance import api

server_logger = structlog.getLogger("server")

"""
orjson override. Force flask to use ORJSON  instead of the native JSON library,
which is way faster, especially on larger datasets

https://medium.com/@catnotfoundnear/finding-the-fastest-python-json-library-on-all-python-versions-8-compared-b7c6dd806c1d

Note - if needed to switch back to json, just comment the import in main
"""

server_logger.info("Registering ORJSON as the Flask-RestX JSON handler")


@api.representation("application/json")
def output_orjson(data, code, headers=None):
    """
    Overrides the default Flask-RESTX JSON serializer to use orjson.
    orjson.dumps returns bytes, which Flask's make_response handles natively.
    """
    # Add orjson.OPT_INDENT_2 for pretty printing
    dumped_bytes = orjson.dumps(data)

    resp = make_response(dumped_bytes, code)
    resp.headers.extend(headers or {})
    return resp
