import re
import tomllib

import structlog

server_logger = structlog.getLogger("server")


# def sanitize_cpp_name(name: str) -> str:
#     clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(name))
#     if clean_name and clean_name[0].isdigit():
#         clean_name = f"_{clean_name}"
#     return clean_name


def sanitize_cpp_name(name: str) -> str:
    """
    Convert an arbitrary string (including pipe paths) into a valid C++ identifier.
    - Replaces anything not [a-zA-Z0-9_] with '_'
    - Adds a leading '_' if the first character is a digit
    """
    # Replace invalid characters (including backslashes, dots, etc.)
    # match anything that's not one of these, and replace with _
    clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(name))

    # Prevent leading digit
    if clean_name and clean_name[0].isdigit():
        clean_name = f"_{clean_name}"

    return clean_name


def generate_toml_smb_context(profile_toml: str, profile_name: str) -> dict:
    server_logger.info("Generating SMB context from TOML profile")

    try:
        data = tomllib.loads(profile_toml)
    except Exception as e:
        server_logger.error("Failed to parse TOML Profile", error=str(e))
        raise e

    smb_get_block = data.get("smb", {}).get("get", {})
    smb_post_block = data.get("smb", {}).get("post", {})

    inbox_pipe_name = smb_get_block.get("pipe_name", "inbox")
    outbox_pipe_name = smb_post_block.get("pipe_name", "outbox")
    return {
        "inbox_pipe_name": inbox_pipe_name,
        "outbox_pipe_name": outbox_pipe_name,
        "namespace_name": sanitize_cpp_name(f"smb_{profile_name}"),
        # "chunk_size":  ...
    }
