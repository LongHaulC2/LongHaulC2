from collections.abc import Mapping
from typing import Any

import structlog
from yarl import URL

from ..utils.checks import check_type

server_log = structlog.getLogger("server")


# todo: find a way to get args/startup things to this later, for more dynamic url generation
# ex, python3 client --host https://127.0.0.1:1234


def generate_url(uri: str, params: Mapping[str, Any] | None = None) -> str:
    """
    Generates a full URL for requests. Handles the schema, and IP/Address of the API.

    :param uri: A uri to convert into a full URL.
                Ex: "/some/endpoint" OR "some/endpoint/"
    :param params: Optional query parameters
                Ex: {"since": "uuid", "limit": 10}. These will get added onto the end like: somepath?param1=somevalue
                TLDR: yarl only wants paths passed to it, and passing `somepath?param1=somevalue` directly, encodes it.
    """
    check_type(uri, str, "uri")

    if params is not None:
        check_type(params, Mapping, "params")

    # Remove leading slash (YARL path-safe)
    if uri.startswith("/"):
        uri = uri[1:]

    HOST = "http://10.0.0.30:45045"

    url = URL(HOST) / uri

    # Attach query parameters correctly
    if params:
        url = url.with_query(params)

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(url=str(url))
    server_log.debug("Generated URL")

    return str(url)
