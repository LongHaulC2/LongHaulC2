import os
import re
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .context_generators.http_wininet import generate_http_wininet_context
from .types import ListenerProfile  # Import your types

server_logger = structlog.getLogger("server")
# TEMPLATE_DIR = Path(__file__).parent / "templates"

workspace_dir = os.getenv("WORKSPACE_DIR", "/var/lib/longhaulc2")
# temp hardcode the win_x64_implant_base
TEMPLATE_DIR = Path(workspace_dir) / "implant_templates" / "win_implant_base" / "templates"


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
    profile_mappings: dict[str, str] = {}

    for uuid, listener in listeners_data_dict.items():
        structlog.contextvars.bind_contextvars(listener_type=listener["listener_type"])

        try:
            mappings = _render_listener_variant(output_dir, listener)

            # Extract the unified namespace we created in the variant function
            ns_name = mappings["namespace"]

            # Store it: e.g., profile_mappings["a"] = "http_10_0_0_30_9090_a"
            profile_mappings[listener["listener_profile_name"]] = ns_name

        except Exception as e:
            server_logger.error("Failed to render listener", listener_uuid=uuid, error=e)
            raise e

    # Retrieve initial namespace names
    init_get_name = listeners_data_dict[initial_get_profile_listener_uuid]["listener_profile_name"]
    init_post_name = listeners_data_dict[initial_post_profile_listener_uuid]["listener_profile_name"]

    init_get_namespace = profile_mappings.get(init_get_name)
    init_post_namespace = profile_mappings.get(init_post_name)

    _render_file(
        output_dir / "core/c2.cpp",
        "c2.j2",
        {
            "profile_mappings": profile_mappings,
            "init_get_namespace": init_get_namespace,
            "init_post_namespace": init_post_namespace,
        },
        mode="w",
    )

    # ! For now, rendering transport as well in here, they have the same req's.
    # move to its own function when needed
    _render_file(
        output_dir / "comms/transport.h",
        "transport.h.j2",
        {
            "profile_mappings": profile_mappings,
            # "get_function_mappings": get_func_mappings,
            # "post_function_mappings": post_func_mappings,
            "init_get_function": init_get_namespace,  # init get and init post not used in this template
            "init_post_function": init_post_namespace,
        },
        mode="w",  # overwrite if there was a file in the template dir
    )


def _render_listener_variant(output_dir: Path, listener: ListenerProfile) -> dict[str, str]:
    """
    Handles the logic for a specific listener type (e.g. HTTP).
    Renders the comms code and returns the UNIFIED function/namespace name.
    """
    listener_type = listener.get("listener_type")
    host = listener.get("listener_host")
    port = listener.get("listener_port")
    prof_name = listener.get("listener_profile_name")

    # Generate ONE unified name. No more "get" or "post" here.
    base_name = f"{host}_{port}_{prof_name}"
    unified_namespace = sanitize_cpp_name(f"http_{base_name}")

    # Generate Context
    context = _get_listener_context(listener)

    # Inject the unified name into the context so the comms.cpp template knows its name
    context["http_function_name"] = unified_namespace

    # Render based on type
    if listener_type == "http":
        _render_file(
            output_dir / "comms/comms.h",
            "wininet_comms_http.j2",
            context,
            mode="a",
        )

        # Return just the one unified namespace
        return {"namespace": unified_namespace}

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

        with Path.open(dest_path, mode) as f:
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
