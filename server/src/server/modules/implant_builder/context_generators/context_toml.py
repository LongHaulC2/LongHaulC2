import re
import tomllib

import structlog

server_logger = structlog.getLogger("server")


def sanitize_cpp_name(name: str) -> str:
    clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(name))
    if clean_name and clean_name[0].isdigit():
        clean_name = f"_{clean_name}"
    return clean_name


def generate_toml_context(profile_toml: str, host: str, port: int, profile_name: str) -> dict:
    server_logger.info("Generating HTTP context from TOML profile")

    try:
        data = tomllib.loads(profile_toml)
    except Exception as e:
        server_logger.error("Failed to parse TOML Profile", error=str(e))
        raise e

    opts = data.get("profile", {}).get("options", {})

    return {
        "callback_host": host,
        "callback_port": port,
        "http_user_agent": opts.get("useragent", "Mozilla/5.0"),
        "http_function_name": sanitize_cpp_name(f"http_{host}_{port}_{profile_name}"),
        # Pass the raw config blocks directly to Jinja
        "get_config": data.get("http", {}).get("get", {}),
        "post_config": data.get("http", {}).get("post", {}),
    }
