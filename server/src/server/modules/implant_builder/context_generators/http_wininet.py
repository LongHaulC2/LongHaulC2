import logging
import tempfile
from pathlib import Path

import structlog
from mpp import *

from ....listeners.malc2 import *  # load_malleable_profile comes from here, along with a few others

server_logger = logging.getLogger("server")


def generate_http_wininet_context(
    malleable_c2_profile: str, callback_host: str, callback_port: int
) -> dict:
    """
    Main entry point to generate the Jinja2 context for HTTP Wininet listeners.
    Parses the Malleable C2 profile and extracts common, GET, and POST configurations.
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        # malleable_c2=Path(malleable_c2_path).name,
        callback_host=callback_host,
        callback_port=callback_port,
    )

    server_logger.info("Generating HTTP Wininet context")

    # 1. Load and Parse Profile
    profile = load_malleable_profile(malleable_c2_profile)

    context = {}

    # 2. Extract Common Options
    context.update(_extract_common_options(profile, callback_host, callback_port))

    # 3. Extract HTTP GET Options
    context.update(_extract_http_get_options(profile))

    # 4. Extract HTTP POST Options
    context.update(_extract_http_post_options(profile))

    # Debug output for verification
    server_logger.debug(f"Context generation complete")

    return context


def _extract_common_options(profile: MalleableProfile, host: str, port: int) -> dict:
    """Extracts global settings like User-Agent."""
    return {
        "http_user_agent": profile.profile.get("useragent", None),
        "callback_host": host,
        "callback_port": port,
    }


def _extract_http_get_options(profile: MalleableProfile) -> dict:
    """Extracts and parses all http-get block configurations."""
    structlog.contextvars.bind_contextvars(section="http_get")
    server_logger.debug("Extracting HTTP GET options")

    context_dict = {
        "http_get_verb": None,
        "http_get_uri": None,
        "http_get_client_metadata_transforms_list": [],
        "http_get_client_metadata_terminator": None,
        "http_get_client_metadata_terminator_value": None,
        "http_get_server_output_transforms_list": [],
        "http_get_client_output_terminator": None,
        "http_get_client_output_terminator_value": None,
        "http_get_client_headers_or_parameters_list": [],
    }

    # --- Client Configuration ---
    client_parser = HttpGetBlockClientParser(profile.http_get.client)

    # URI
    context_dict["http_get_uri"] = profile.http_get.uri.value

    # Verb (Default to GET if missing)
    verb = getattr(profile.http_get, "verb", None)
    context_dict["http_get_verb"] = verb.value if verb is not None else "GET"

    # Transforms (Client Metadata)
    context_dict["http_get_client_metadata_transforms_list"] = (
        client_parser.get_client_metadata_transforms_list()
    )

    # Terminator (Where to store metadata)
    term_type, term_value = client_parser.get_metadata_terminator()
    if term_type == "header":
        context_dict["http_get_client_metadata_terminator"] = "header"
        context_dict["http_get_client_metadata_terminator_value"] = term_value
    elif term_type == "parameter":
        context_dict["http_get_client_metadata_terminator"] = "parameter"
        context_dict["http_get_client_metadata_terminator_value"] = term_value
    elif term_type == "uri-append":
        context_dict["http_get_client_metadata_terminator"] = "uri-append"
        context_dict["http_get_client_metadata_terminator_value"] = (
            term_value  # shuold be none
        )
    elif term_type == "print":
        context_dict["http_get_client_metadata_terminator"] = "print"
        context_dict["http_get_client_metadata_terminator_value"] = (
            term_value  # should be none
        )
    # Add other cases (uri, etc) here as needed

    # List of headers or parameters to add to the request
    """
    [{'name': 'parameter', 'key': 'utmac', 'value': 'UA-2202604-2'}, {'name': 'parameter', 'key': 'utmcn', 'value': '1'}, {'name': 'parameter', 'key': 'utmcs', 'value': 'ISO-8859-1'}, {'name': 'parameter', 'key': 'utmsr', 'value': '1280x1024'}, {'name': 'parameter', 'key': 'utmsc', 'value': '32-bit'}, {'name': 'parameter', 'key': 'utmul', 'value': 'en-US'}]    
    """
    headers_and_parameters_list = client_parser.get_headers_and_parameters_list()
    context_dict["http_get_client_headers_or_parameters_list"] = (
        headers_and_parameters_list
    )

    # --- Server Configuration ---
    server_parser = HttpGetBlockServerParser(profile.http_get.server)

    # Transforms (Server Output)
    # Note: Reversed because the implant must undo what the server did
    context_dict["http_get_server_output_transforms_list"] = list(
        # don't use .reverse cuz that returns none
        reversed(server_parser.get_server_output_transforms_list())
    )

    # Terminator (Where to find output from server, aka task)
    out_type, out_value = server_parser.get_output_terminator()
    match out_type:
        case "header":
            context_dict["http_get_client_output_terminator"] = "header"
            context_dict["http_get_client_output_terminator_value"] = out_value
        case "print":
            context_dict["http_get_client_output_terminator"] = "print"

    return context_dict


def _extract_http_post_options(profile: MalleableProfile) -> dict:
    """Extracts and parses all http-post block configurations."""
    structlog.contextvars.bind_contextvars(section="http_post")
    server_logger.debug("Extracting HTTP POST options")

    context_dict = {
        "http_post_verb": None,
        "http_post_uri": None,
        "http_post_client_id_transforms_list": [],
        "http_post_client_id_terminator": None,
        "http_post_client_id_terminator_value": None,
        "http_post_client_output_transforms_list": [],
        "http_post_client_output_terminator": None,
        "http_post_client_output_terminator_value": None,
    }

    # --- Client Configuration ---
    client_parser = HttpPostBlockClientParser(profile.http_post.client)

    # URI
    context_dict["http_post_uri"] = profile.http_post.uri.value

    # Verb (Default to POST if missing)
    verb = getattr(profile.http_post, "verb", None)
    context_dict["http_post_verb"] = verb.value if verb is not None else "POST"

    # Transforms (Client ID)
    context_dict["http_post_client_id_transforms_list"] = (
        client_parser.post_client_id_transforms_list()
    )

    # get addtl headers/params
    headers_and_parameters_list = client_parser.get_headers_and_parameters_list()
    context_dict["http_post_client_headers_or_parameters_list"] = (
        headers_and_parameters_list
    )

    # Terminator (ID)
    id_term_type, id_term_value = client_parser.get_id_terminator()
    match id_term_type:
        case "header":
            context_dict["http_post_client_id_terminator"] = "header"
            context_dict["http_post_client_id_terminator_value"] = id_term_value
        case "parameter":
            context_dict["http_post_client_id_terminator"] = "parameter"
            context_dict["http_post_client_id_terminator_value"] = id_term_value
        # not sure if allowed
        case "uri-append":
            context_dict["http_post_client_id_terminator"] = "uri-append"
            context_dict["http_post_client_id_terminator_value"] = id_term_value
        case "print":
            context_dict["http_post_client_id_terminator"] = "print"

    # Transforms (Client Output)
    context_dict["http_post_client_output_transforms_list"] = (
        client_parser.post_client_output_transforms_list()
    )

    # Terminator (Output/Response)
    out_term_type, out_term_value = client_parser.get_output_terminator()
    match out_term_type:
        case "header":
            context_dict["http_post_client_output_terminator"] = "header"
            context_dict["http_post_client_output_terminator_value"] = out_term_value
        case "parameter":
            context_dict["http_post_client_output_terminator"] = "parameter"
            context_dict["http_post_client_output_terminator_value"] = out_term_value
        case "uri-append":
            context_dict["http_post_client_output_terminator"] = "uri-append"
            context_dict["http_post_client_output_terminator_value"] = out_term_value
        case "print":
            context_dict["http_post_client_output_terminator"] = "print"

    return context_dict
