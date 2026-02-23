import re
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .context_generators.http_wininet import generate_http_wininet_context
from .types import FunctionMapping, ListenerProfile  # Import your types

server_logger = structlog.getLogger("server")
TEMPLATE_DIR = Path(__file__).parent / "templates"

# Initialize Jinja Environment once
ENV = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR.resolve()),
    block_start_string="[%",
    block_end_string="%]",
    variable_start_string="[[",
    variable_end_string="]]",
    comment_start_string="[#",
    comment_end_string="#]",
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=StrictUndefined,
)


def render_implant(
    output_dir: Path,
    listeners_data_dict: dict[str, ListenerProfile],
    initial_get_profile_listener_uuid: str,
    initial_post_profile_listener_uuid: str,
):
    """
    Main entry point for rendering C++ files.
    1. Renders individual comms files (comms.cpp)
    2. Maps function names for polymorphism
    3. Renders the main controller (c2.cpp)
    """

    # Mappings for c2.cpp: { "profile_name": { "key": sanitized, "value": actual } }
    get_func_mappings: dict[str, FunctionMapping] = {}
    post_func_mappings: dict[str, FunctionMapping] = {}

    # Render Listener Communication Modules (comms.cpp)
    # This loop appends code to comms.cpp for every listener
    for uuid, listener in listeners_data_dict.items():
        # Setup Logger Context
        # print(listeners_data_dict)
        structlog.contextvars.bind_contextvars(listener_type=listener["listener_type"])

        # Generate Context & Mappings
        try:
            mappings = _render_listener_variant(output_dir, listener)

            # Update the master mapping dicts
            profile_name = listener["listener_profile_name"]
            get_func_mappings[profile_name] = mappings["get"]
            post_func_mappings[profile_name] = mappings["post"]

        except Exception as e:
            server_logger.error("Failed to render listener", listener_uuid=uuid, error=e)
            raise e

    # Determine Initial Profile Functions
    # Retrieve the profile name associated with the initial UUIDs
    init_get_name = listeners_data_dict[initial_get_profile_listener_uuid]["listener_profile_name"]
    init_post_name = listeners_data_dict[initial_post_profile_listener_uuid]["listener_profile_name"]
    # Lookup the sanitized C++ function name
    init_get_func = get_func_mappings.get(init_get_name, {}).get("value")
    init_post_func = post_func_mappings.get(init_post_name, {}).get("value")

    # Render Controller (c2.cpp)
    _render_file(
        output_dir / "control/c2.cpp",
        "c2.j2",
        {
            "get_function_mappings": get_func_mappings,
            "post_function_mappings": post_func_mappings,
            "init_get_function": init_get_func,
            "init_post_function": init_post_func,
        },
        mode="w",  # overwrite if there was a file in the template dir
    )


def _render_listener_variant(output_dir: Path, listener: ListenerProfile) -> dict[str, FunctionMapping]:
    """
    Handles the logic for a specific listener type (e.g. HTTP).
    Renders the comms code and returns the function names generated.
    """
    listener_type = listener.get("listener_type")
    host = listener.get("listener_host")
    port = listener.get("listener_port")
    prof_name = listener.get("listener_profile_name")

    # Generate Context
    context = _get_listener_context(listener)

    # Render based on type
    if listener_type == "http":
        # Render comms.cpp (Append mode)
        _render_file(
            output_dir / "lifecycle/comms.cpp",
            "wininet_comms_http.j2",
            context,
            mode="a",  # append here, as there are multiple profiles being added to the file.
        )

        # Generate Function Names for the map
        # Naming convention: http_get_HOST_PORT_PROFILENAME
        base_name = f"{host}_{port}_{prof_name}"
        get_func = sanitize_cpp_name(f"http_get_{base_name}")
        post_func = sanitize_cpp_name(f"http_post_{base_name}")

        return {
            "get": {"key": get_func, "value": get_func},
            "post": {"key": post_func, "value": post_func},
        }

    else:
        raise ValueError(f"Unsupported listener type: {listener_type}")


def _get_listener_context(listener: ListenerProfile) -> dict:
    """Delegates context generation to specific modules."""
    listener_type = listener.get("listener_type")

    if listener_type == "http":
        return generate_http_wininet_context(
            listener.get("listener_profile_contents"),
            listener.get("listener_host"),
            listener.get("listener_port"),
            listener.get("listener_profile_name"),
        )
    return {}


def _render_file(dest_path: Path, template_name: str, context: dict, mode: str = "w"):
    """
    Generic render helper.
    mode='w' for write/overwrite
    mode='a' for append
    """
    structlog.contextvars.bind_contextvars(template=template_name)

    try:
        template = ENV.get_template(template_name)
        rendered_code = template.render(**context)

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, mode) as f:
            f.write(rendered_code)

    except Exception as e:
        server_logger.error("Template render error", template_name=template_name, error=e)
        raise e


def sanitize_cpp_name(name: str) -> str:
    """
    Converts a string into a valid C++ function/variable name.
    """
    clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(name))
    if clean_name[0].isdigit():
        clean_name = f"_{clean_name}"
    return clean_name
