import re
import tomllib

import structlog

server_logger = structlog.getLogger("server")


def sanitize_cpp_name(name: str) -> str:
    clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(name))
    if clean_name and clean_name[0].isdigit():
        clean_name = f"_{clean_name}"
    return clean_name


def generate_toml_raw_context(
    profile_toml: str,
    host: str,
    port: int,
    profile_name: str,
) -> dict:
    """
    Parse the [raw.get] / [raw.post] block from the TOML profile and return
    a flat Jinja context dict for the raw_comms.h.j2 template.

    Transform lists are pre-extracted here so the template never needs to do deep
    dict access through potentially-missing keys (avoids StrictUndefined issues).
    """
    server_logger.info("Generating raw socket context from TOML profile")

    try:
        data = tomllib.loads(profile_toml)
    except Exception as e:
        server_logger.error("Failed to parse TOML profile for raw context", error=str(e))
        raise

    raw_block = data.get("raw", {})
    get_block = raw_block.get("get", {})
    post_block = raw_block.get("post", {})

    return {
        "callback_host": host,
        "callback_port": port,
        "raw_profile_namespace": sanitize_cpp_name(f"raw_{host}_{port}_{profile_name}"),
        "raw_proto": get_block.get("proto", "tcp").lower(),
        # Body templates
        "get_body": get_block.get("body", "<METADATA>"),
        "post_body": post_block.get("body", "<OUTPUT>"),
        "get_server_body": get_block.get("server", {}).get("body", "<OUTPUT>"),
        "post_server_body": post_block.get("server", {}).get("body", ""),
        # Transform lists (pre-extracted so Jinja doesn't need to traverse nested dicts)
        "get_metadata_transforms": get_block.get("client", {}).get("metadata", {}).get("transforms", []),
        "get_server_transforms": get_block.get("server", {}).get("output", {}).get("transforms", []),
        "post_id_transforms": post_block.get("client", {}).get("id", {}).get("transforms", []),
        "post_output_transforms": post_block.get("client", {}).get("output", {}).get("transforms", []),
    }
