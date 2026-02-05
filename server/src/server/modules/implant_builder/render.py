import logging
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from mpp import MalleableProfile

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
    # clean up whitespace so generated code looks not like shit
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=StrictUndefined,  # Fail fast if a var is missing
)


def render_implant(
    output_dir: Path,
    listeners_data_dict,
):
    # server_logger.debug(f"Rendering Implant: {listeners_data_dict}")

    # dict to hold all the contexts for each profile
    dict_of_contexts = {}
    # 3. Define the File Map
    files_to_render = {}
    # ex, {"output/path/file.cpp": {"jinja_template_file": "template.j2", "context": {...}}}

    # construct malleable_c2_profile_dict (dict of {"name":"contents_of_profile"})
    malleable_c2_profile_dict = {}

    dict_of_post_function_mappings = {}  # {"http_get_amazon":"http_get_profname"}
    dict_of_get_function_mappings = {}  # {"http_get_amazon":"http_get_profname"}

    # move to functions later:
    # =============
    # comms.cpp render chain
    # =============
    for listener_key, listener_data in listeners_data_dict.items():
        # server_logger.debug(f"listener_data: {listener_data}")

        print(listener_key)
        print(listener_data)
        mc2_name = listener_data.get("listener_profile_name")
        mc2_contents = listener_data.get("listener_profile_contents")
        # add to dict
        malleable_c2_profile_dict[mc2_name] = mc2_contents

        # extract listener info
        listener_type = listener_data.get("listener_type")
        callback_host = listener_data.get("listener_host")
        callback_port = listener_data.get("listener_port")

        # 1. Logging Setup
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            output_dir=output_dir,
            listener_type=listener_type,
        )
        server_logger.debug("_create_implant")

        # 2. Build the Aggregate Context, from this profile
        # We build a master dictionary containing the specific context for EVERY profile.
        # for name, content in malleable_c2_profile_dict.items():
        # dict_of_contexts[mc2_name] =
        context = extract_context(
            mc2_contents,
            listener_type,
            callback_host,
            callback_port,
            mc2_name,
        )

        # Add Listener Specific files to the render list, based on variant.
        match listener_type:
            case "http":
                # files_to_render[output_dir / "lifecycle/comms.cpp"] = {
                #     "jinja_template_file": "wininet_comms_http.j2",
                #     # Wrap it in a key (e.g. 'profiles') so Jinja can iterate:
                #     # {% for name, ctx in profiles.items() %}
                #     "context": context,
                # }

                current_render_job = {
                    output_dir
                    / "lifecycle/comms.cpp": {
                        "jinja_template_file": "wininet_comms_http.j2",
                        "context": context,
                    }
                }
                # render and write immediately to avoid overwriting comms.cpp from multiple listeners
                # a previous bug was using the same dict key, this fixes it without a big refactor
                render_and_write_comms_cpp(current_render_job)

                # add to mappings, this is used for the c2.j2, to map these func names to the implant.
                get_function_name = (
                    f"http_get_{callback_host}_{callback_port}_{mc2_name}"
                )
                post_function_name = (
                    f"http_post_{callback_host}_{callback_port}_{mc2_name}"
                )
                dict_of_get_function_mappings[mc2_name] = {
                    # I know I'm assigning these to themselves, tldr, it's easier.
                    # output: "http_get_amason.com_6769_amazongetprofile": "http_get_amason.com_6769_amazongetprofile",
                    "key": sanitize_cpp_name(get_function_name),
                    "value": sanitize_cpp_name(get_function_name),
                }
                dict_of_post_function_mappings[mc2_name] = {
                    # I know I'm assigning these to themselves, tldr, it's easier.
                    # output: "http_get_amason.com_6769_amazongetprofile": "http_get_amason.com_6769_amazongetprofile",
                    "key": sanitize_cpp_name(post_function_name),
                    "value": sanitize_cpp_name(post_function_name),
                }
            case _:
                server_logger.error(f"Invalid listener type: {listener_type}")
                raise ValueError(f"Invalid listener type: {listener_type}")

    # okay goal here - dump rendered items into theier files,
    # however, comms.cpp needs to all go into one file, not sure how to do that with
    # this logic yet. Maybe a list of rendered files, then use the templting to do that ig.

    render_and_write_c2_j2(
        output_dir, dict_of_get_function_mappings, dict_of_post_function_mappings
    )

    # render_and_write_comms_cpp(files_to_render)


def render_file(template_file: str, context: dict) -> str:
    """Render a file based on the template provided

    NOTE: When saving a file, this will APPEND to existing files, not overwrite.
    This is a hack to allow multiple templates to contribute to the same output file... it's fine.

    Args:
        template_file (str): Path to template file
        context (dict): context to fill in template with

    Raises:
        e: error
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(template=str(template_file), context=context)
    server_logger.debug("Rendering file")

    try:
        # Load by name
        template = env.get_template(template_file)
        rendered_code = template.render(**context)

        return rendered_code

        server_logger.debug(f"Rendered successfully")

    except Exception as e:
        server_logger.error(f"Error rendering: {e}")
        raise e


def extract_context(
    malleable_c2_profile,
    listener_type,
    callback_host,
    callback_port,
    malleable_c2_profile_name,
) -> dict:
    """
    Extracts and returns the context for a given listener type
    """
    global_context = {}
    match listener_type:
        case "http":
            global_context = generate_http_wininet_context(
                malleable_c2_profile,
                callback_host,
                callback_port,
                malleable_c2_profile_name,
            )

        case _:
            server_logger.error(f"Invalid listener type: {listener_type}")
    return global_context


# individualized render functions for each file type - TLDR, makes code much cleaner & seperation "more better"


def render_and_write_comms_cpp(files_to_render):
    # write the comms.cpp file first - note, this appends.
    for dest_file, render_dict in files_to_render.items():
        # Ensure directory exists
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        render_context = render_dict.get("context")
        jinja_template_file = render_dict.get("jinja_template_file")

        # name of .j2 file
        jinja_template_file = jinja_template_file
        # the dict with all the context *for* the file
        jinja_template_context = render_context

        rendered_code = render_file(jinja_template_file, jinja_template_context)

        # Ensure output directory exists & write to file
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_file, "a") as f:
            f.write(rendered_code)


def render_and_write_c2_j2(
    output_dir: Path,
    dict_of_get_function_mappings: dict,
    dict_of_post_function_mappings: dict,
):
    # =============
    # c2.cpp render chain
    # =============
    #  See todo, tldr; `s_ingress_map["http_get_amazon"] = get_HTTP;` rendering here.
    # ex: `s_ingress_map["profile_name"] = profile_function_name;`
    # take the mappings

    # 4. Execution Loop
    server_logger.info("Rendering Implant Files")
    dest_file = output_dir / "control/c2.cpp"

    rendered_code = render_file(
        "c2.j2",
        {
            "get_function_mappings": dict_of_get_function_mappings,
            "post_function_mappings": dict_of_post_function_mappings,
            "init_get_function": next(
                iter(dict_of_get_function_mappings.values()), None
            ),  # get first item. Have user specified later?
            "init_post_function": next(
                iter(dict_of_post_function_mappings.values()), None
            ),  # also first item. Have user specified later?, i.e., choose a starter listener, then have extras in there for chanign
        },
    )

    dest_file.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_file, "w") as f:
        f.write(rendered_code)


def sanitize_cpp_name(name: str) -> str:
    """
    Converts a string into a valid C++ function/variable name.
    1. Replaces non-alphanumeric chars (like . - @ spaces) with underscores.
    2. Ensures it doesn't start with a number.
    """
    # Replace anything that isn't a-z, A-Z, 0-9, or _ with an underscore
    clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)

    # If the first character is a number, prepend an underscore
    if clean_name[0].isdigit():
        clean_name = f"_{clean_name}"

    return clean_name
