import re
import tomllib

import structlog

from ....listeners.transform import malleable_string_to_bytes

server_logger = structlog.getLogger("server")


def _val_to_cpp_octal(val_str: str) -> str:
    r"""Re-encode a TOML transform val as C++ octal escapes to prevent hex-bleed.

    C++ \x is greedy and consumes all following hex digits, so \x0A226 becomes
    codepoint 0x0A226 instead of \x0A followed by '226'. Octal escapes (\NNN)
    always stop after 3 digits, so \015\012226 is unambiguous.
    """
    raw = malleable_string_to_bytes(val_str)
    out = []
    for b in raw:
        if b == ord('"'):
            out.append('\\"')
        elif b == ord("\\"):
            out.append("\\\\")
        elif 32 <= b < 127:
            out.append(chr(b))
        else:
            out.append(f"\\{b:03o}")
    return "".join(out)


def _cpp_safe_transforms(transforms: list) -> list:
    out = []
    for t in transforms:
        t = {**t}
        if "key" in t and "val" not in t:
            t["val"] = t.pop("key")
        if "val" in t:
            t["val"] = _val_to_cpp_octal(t["val"])
        out.append(t)
    return out


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
        # Transform lists — vals are re-encoded as C++ octal escapes to prevent hex-bleed
        "get_metadata_transforms": _cpp_safe_transforms(
            get_block.get("client", {}).get("metadata", {}).get("transforms", [])
        ),
        "get_server_transforms": _cpp_safe_transforms(
            get_block.get("server", {}).get("output", {}).get("transforms", [])
        ),
        "post_id_transforms": _cpp_safe_transforms(post_block.get("client", {}).get("id", {}).get("transforms", [])),
        "post_output_transforms": _cpp_safe_transforms(
            post_block.get("client", {}).get("output", {}).get("transforms", [])
        ),
    }
