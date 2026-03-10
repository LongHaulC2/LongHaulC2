import re
import tomllib  # Built into Python 3.11+ (use 'toml' package if older)

import structlog

server_logger = structlog.getLogger("server")


def sanitize_cpp_name(name: str) -> str:
    """
    Converts a string into a valid C++ function/variable name.
    """
    clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if clean_name and clean_name[0].isdigit():
        clean_name = f"_{clean_name}"
    return clean_name


def format_transforms(chain: list) -> list:
    """
    Bridges the gap between the TOML {op='x', val='y'} format
    and the old mpp Statement format expected by Jinja.
    """
    transforms = []
    for step in chain:
        # Ignore 'print' here as it's typically treated as a terminator, not a transform
        if step.get("op") != "print":
            transforms.append({"statement": step.get("op"), "value": step.get("val", "")})
    return transforms


def generate_http_wininet_context(
    malleable_c2_profile_toml: str,
    callback_host: str,
    callback_port: int,
    malleable_c2_profile_name: str,
) -> dict:
    """
    Main entry point to generate the Jinja2 context for HTTP Wininet listeners.
    Parses the LongHaul TOML profile and extracts configurations into the legacy dict structure.
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        callback_host=callback_host,
        callback_port=callback_port,
    )

    server_logger.info("Generating HTTP Wininet context from TOML")

    # 1. Load the TOML
    try:
        profile_data = tomllib.loads(malleable_c2_profile_toml)
    except Exception as e:
        server_logger.error("Failed to parse TOML Profile", error=str(e))
        raise e

    context = {}

    # 2. Extract Common Options
    opts = profile_data.get("profile", {}).get("options", {})
    context.update(
        {
            "http_user_agent": opts.get("useragent", "Mozilla/5.0"),
            "callback_host": callback_host,
            "callback_port": callback_port,
            "http_function_name": sanitize_cpp_name(
                f"http_{callback_host}_{callback_port}_{malleable_c2_profile_name}"
            ),
        }
    )

    # Global Headers
    global_headers = profile_data.get("http", {}).get("global_headers", {})

    # ==========================================
    # 3. Extract HTTP GET Options
    # ==========================================
    structlog.contextvars.bind_contextvars(section="http_get")
    http_get = profile_data.get("http", {}).get("get", {})
    get_client = http_get.get("client", {})
    get_server = http_get.get("server", {})

    # Combine global headers and specific headers/parameters for GET
    get_headers_params = [{"name": "header", "key": k, "value": v} for k, v in global_headers.items()]

    # Identify GET Terminators
    get_client_term = "header" if "header" in get_client else None
    get_client_term_val = get_client.get("header")

    get_server_term = "print" if get_server.get("behavior") == "print" else None

    context.update(
        {
            "http_get_verb": "GET",
            "http_get_uri": http_get.get("uri", ""),
            "http_get_client_metadata_transforms_list": format_transforms(get_client.get("metadata_chain", [])),
            "http_get_client_metadata_terminator": get_client_term,
            "http_get_client_metadata_terminator_value": get_client_term_val,
            "http_get_server_output_transforms_list": [],  # No explicit server undo transforms defined in this TOML snippet
            "http_get_client_output_terminator": get_server_term,
            "http_get_client_output_terminator_value": None,
            "http_get_client_headers_or_parameters_list": get_headers_params,
        }
    )

    # ==========================================
    # 4. Extract HTTP POST Options
    # ==========================================
    structlog.contextvars.bind_contextvars(section="http_post")
    http_post = profile_data.get("http", {}).get("post", {})
    post_client = http_post.get("client", {})

    # Combine headers and parameters for POST
    post_headers_params = [{"name": "header", "key": k, "value": v} for k, v in global_headers.items()]
    for k, v in post_client.get("headers", {}).items():
        post_headers_params.append({"name": "header", "key": k, "value": v})

    post_id_term = None
    post_id_term_val = None

    # Parse parameters, separate the ID parameter from the standard parameters
    for p in post_client.get("params", []):
        if p.get("type") == "id":
            post_id_term = "parameter"
            post_id_term_val = p.get("name")
        else:
            post_headers_params.append({"name": "parameter", "key": p.get("name"), "value": p.get("val")})

    # Find the output terminator (look for the 'print' op in the chain)
    out_chain = post_client.get("output_chain", [])
    post_out_term = "print" if any(step.get("op") == "print" for step in out_chain) else None

    context.update(
        {
            "http_post_verb": "POST",
            "http_post_uri": http_post.get("uri", ""),
            "http_post_client_id_transforms_list": [],  # No explicit ID transform chain defined in TOML snippet
            "http_post_client_id_terminator": post_id_term,
            "http_post_client_id_terminator_value": post_id_term_val,
            "http_post_client_output_transforms_list": format_transforms(out_chain),
            "http_post_client_output_terminator": post_out_term,
            "http_post_client_output_terminator_value": None,
            "http_post_client_headers_or_parameters_list": post_headers_params,
        }
    )

    server_logger.debug("Context generation complete")
    return context
