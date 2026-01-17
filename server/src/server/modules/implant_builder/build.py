import logging
import shutil
import tempfile
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from mpp import *

# OUTPUT_DIR = Path("./templates/output")
IMPLANT_BASE = (
    # this file, up one dir, to implant_base
    Path(__file__).parent
    / "implant_base"
)
# this file, up one dir, to templates
TEMPLATE_DIR = Path(__file__).parent / "templates"


# 1. Setup Jinja with C++ safe delimiters
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

import functools

server_logger = logging.getLogger("server")


def create_implant(malleable_c2_path, listener_type):

    # temp overwrite for mallc2
    mc2_path = Path("/home/ubuntu-dev/LongHaulC2/tests/profiles/webbug.profile")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        listener_type=listener_type, malleable_c2=mc2_path.name
    )
    server_logger.info("Generating implant")

    # The directory is created when entering the block
    with tempfile.TemporaryDirectory(delete=False) as tmp_dir:
        server_logger.debug(f"Creating implant at {tmp_dir}")
        # creat base implant structure
        copy_base_structure(source_dir=IMPLANT_BASE, dest_dir=Path(tmp_dir).resolve())

        # print(f"File created: {temp_file}")
        _create_implant(
            output_dir=Path(tmp_dir).resolve(),
            malleable_c2_path=str(mc2_path),
            listener_type=listener_type,
        )


def _create_implant(output_dir: Path, malleable_c2_path, listener_type):

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        output_dir=output_dir,
        malleable_c2_path=malleable_c2_path,
        listener_type=listener_type,
    )
    server_logger.debug("_create_implant")

    # 1. Get the shared context (Data usually needed by ALL files)
    # global_context = get_context(malleable_c2_path)

    # temp hardcode fro http listener
    global_context = http_wininet_context(malleable_c2_path)

    # 2. Define the File Map
    # Structure: "Destination Path" : "Source Template"
    files_to_render = {}

    # A. Always include Core files (Tasking, Config, Main)
    # files_to_render[OUTPUT_DIR / "core/tasking.cpp"] = "core/tasking.cpp.jinja"
    # files_to_render[OUTPUT_DIR / "main.cpp"] = "core/main.cpp.jinja"

    # copy listener base to temp dir

    # Add Listener Specific files
    match listener_type:
        case "http_wininet":
            # need to edit to...
            # 1. render comms template with stuff
            # 2. write to comms.cpp
            # get/post

            # render and save to comms.cpp... (high level http funcsd)
            files_to_render[output_dir / "lifecycle/comms.cpp"] = (
                "wininet_comms_http.j2"  # no need to prefix, already searching in templates dir
            )
            # copy in .h from template to new dir - note, it's already there from original copy s o maybe this is not needed atm if functions don't change.
            # comms_h_og = Path(IMPLANT_BASE / "lifecycle" / "comms.h")
            # comms_h_dest = Path(output_dir / "lifecycle" / "comms.h")
            # copy_file(comms_h_og, comms_h_dest)

            # render and save to http.cpp... (this is the lib implemetnation for http)
            files_to_render[output_dir / "protocols/http_wininet/http.cpp"] = (
                "wininet_http.j2"
            )

            # render and save to register.cpp... (this is the high level implemetnation for register)
            files_to_render[output_dir / "lifecycle/register.cpp"] = (
                "wininet_register_http.j2"
            )

        # case "smb_named_pipe":
        #     global_context["protocol"] = "SMB"
        #     files_to_render[OUTPUT_DIR / "comms/transport.cpp"] = (
        #         "protocols/smb/pipe.cpp.jinja"
        #     )

        case _:
            raise ValueError(f"Unknown listener type: {listener_type}")

    # 3. Execution Loop
    # Iterate over the dict and build everything
    server_logger.debug(f"Building implant")
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


def copy_file(source: Path, dest: Path):
    """
    Copies a file from source to dest, ensuring the destination directory exists.
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(source=source, dest=dest)
    server_logger.debug(f"Copying file")

    # 1. Sanity Check
    if not source.exists():
        server_logger.error(f"Error: Source file missing: {source}")
        return

    # 2. Create the folder structure if it doesn't exist
    # (e.g., if dest is 'build/libs/core.lib', this makes 'build/libs/')
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        # 3. Copy (copy2 preserves metadata like timestamps)
        shutil.copy2(source, dest)
        server_logger.info(f"Copied: {source.name} -> {dest}")

    except Exception as e:
        server_logger.error(f"[!] Failed to copy {source}: {e}")
        raise e


def copy_base_structure(source_dir: Path, dest_dir: Path):
    """
    Recursively copies the entire folder structure from source to dest.
    If dest_dir already exists, it merges/overwrites thanks to dirs_exist_ok=True.
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        source_dir=str(source_dir), dest_dir=str(dest_dir)
    )
    server_logger.debug("Copying base structure into temp directory")

    if not source_dir.exists():
        server_logger.error(f"[!] Base structure missing: {source_dir}")
        return

    try:
        shutil.copytree(
            source_dir,
            dest_dir,
            dirs_exist_ok=True,
        )
    except Exception as e:
        server_logger.error(f"Error copying base structure")
        raise e


from ...listeners.malc2 import *


def http_wininet_context(malleable_c2_str):
    """
    http_wininet function for getting needed keys from malleable c2.


    """
    """
    Quick explanation, mp takes a file, not a string (it has a from_string method... but it wasn't working)
    So, tempfile on the host, then pass that into the mp parser. Whatever, it works well enough. 

    Tried StringIO, didn't work either
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(malleable_c2=Path(malleable_c2_str).name)
    server_logger.debug(f"Gathering data from Malleable C2 profile")

    # temp read it
    with open(malleable_c2_str, "r") as file:
        f = file.read()

    with tempfile.NamedTemporaryFile("w+", suffix=".profile") as tmp_file:
        tmp_file.write(f)
        tmp_file.flush()
        mp = MalleableProfile(profile=tmp_file.name)

        # could also include the malleable c2 file in the code dir and read it from there

        # alllll options here.

    server_logger.info(f"Generating context for implant build")

    context = {}

    # =======================
    # Misc
    # =======================
    context["http_user_agent"] = "NOTIMPLEMENTED_USERAGENT"  # from malc2
    context["callback_host"] = "NOTIMPLEMENTED_CALLBACKHOST"  # from funcitno
    context["callback_port"] = "NOTIMPLEMENTED_CALLBACKPORT"  # from function

    # =======================
    # HTTP_GET options
    # =======================
    # init keys
    context["http_get_uri"] = None
    context["http_get_verb"] = "GET"  # default to get

    context["http_client_metadata_transforms"] = []
    context["http_get_client_metadata_terminator"] = None
    context["http_get_client_metadata_terminator_value"] = None

    context["http_get_server_output_transforms"] = []
    context["http_client_metadata_terminator"] = None
    context["http_client_metadata_terminator_value"] = None

    hce = HttpGetBlockClientParser(mp.http_get.client)
    # start with URI
    context["http_get_uri"] = mp.http_get.uri.value

    # now onto blocks...
    # get client parameters/headers to add on, etc.

    # [list] get metadata tranforms (exclude final statement)
    context["http_client_metadata_transforms"] = []

    # get where to store metadata
    terminator_type, terminator_value = hce.get_metadata_terminator()
    match terminator_type:
        case "header":
            context["http_get_client_metadata_terminator"] = "header"
            context["http_get_client_metadata_terminator_value"] = terminator_value

        # case "uri":
        #     ...

    # server side adjustmetns
    hce = HttpGetBlockServerParser(mp.http_get.server)
    # now onto blocks...
    # get client parameters/headers to add on, etc.

    # [list] get metadata tranforms (exclude final statement)
    context["http_get_server_output_transforms"] = []

    # get where to store output (task)
    terminator_type, terminator_value = hce.get_output_terminator()
    match terminator_type:
        case "header":
            context["http_get_client_output_terminator"] = "header"
            context["http_get_client_output_terminator_value"] = terminator_value

        case "print":
            context["http_get_client_output_terminator"] = "print"
            # no value, print goes straight to body
            # context["http_client_metadata_terminator_value"] = terminator_value

        # case "uri":
        #     ...

    # =======================
    # HTTP_POST options
    # =======================
    # client options
    context["http_post_verb"] = "POST"  # default to post
    context["http_post_uri"] = None

    # Init options so they don't get forgotten
    # set these to none initially, for jinja purposes
    context["http_post_client_id_terminator"] = None
    context["http_post_client_id_terminator_value"] = None

    # set to none to init
    context["http_post_client_output_terminator"] = None
    context["http_post_client_output_terminator_value"] = None

    # server options
    hce = HttpPostBlockClientParser(mp.http_post.client)
    # now onto blocks...
    # get client parameters/headers to add on, etc.

    # [list] get transforms for id coming back in
    context["http_post_client_id_transforms"] = []

    # get where to store id (task)
    terminator_type, terminator_value = hce.get_id_terminator()
    match terminator_type:
        case "header":
            context["http_post_client_id_terminator"] = "header"
            context["http_post_client_id_terminator_value"] = terminator_value

        case "print":
            context["http_post_client_id_terminator"] = "print"
            # no value, print goes straight to body
            # context["http_client_metadata_terminator_value"] = terminator_value

    # [list] get transforms for data coming back in
    context["http_post_client_output_transforms"] = []

    # get where to post data back to
    terminator_type, terminator_value = hce.get_output_terminator()
    match terminator_type:
        case "header":
            # put task response in header
            context["http_post_client_output_terminator"] = "header"
            # what header to store response in
            context["http_post_client_output_terminator_value"] = terminator_value

        case "print":
            context["http_post_client_output_terminator"] = "print"
            # no value, print goes straight to body
            # context["http_client_metadata_terminator_value"] = terminator_value

        # case "uri":
        #     ...

    """
    Naming convention, key, but with _ instead of .

    """
    # context = {
    #     # Returns "value" or None.
    #     # client
    #     "http_get_client_metadata_header": get(mp, "http_get.client.metadata.header"),
    #     # server
    #     "http_post_server_id_header": get(mp, "http_post.server.id.header"),
    #     "http_post_server_output_header": get(mp, "http_post.server.output.header"),
    #     # # Works for deeper nested stuff
    #     # "session_id":      get(mp, "http_get.client.id.parameter"),
    #     # # Works for top level
    #     # "jitter":          get(mp, "jitter"),
    #     # # Handles missing stuff gracefully (returns None)
    #     # "does_not_exist":  get(mp, "http_get.client.fake_block.garbage")
    # }

    for i, j in context.items():
        print(f"{i}:{j}")

    return context

    ...


def get_context(malleable_c2_str):
    """
    Gets malleablec2 data from malleablce2 and reutnrs as a big dict?

    :param malleable_c2: Description
    """

    """
    Quick explanation, mp takes a file, not a string (it has a from_string method... but it wasn't working)
    So, tempfile on the host, then pass that into the mp parser. Whatever, it works well enough. 

    Tried StringIO, didn't work either
    """
    # temp read it
    with open(malleable_c2_str, "r") as file:
        f = file.read()

    with tempfile.NamedTemporaryFile("w+", suffix=".profile") as tmp_file:
        tmp_file.write(f)
        tmp_file.flush()
        mp = MalleableProfile(profile=tmp_file.name)

        # could also include the malleable c2 file in the code dir and read it from there

        # alllll options here.

    """
    Naming convention, key, but with _ instead of .

    """
    context = {
        # Returns "value" or None.
        # client
        "http_get_client_metadata_header": get(mp, "http_get.client.metadata.header"),
        # server
        "http_post_server_id_header": get(mp, "http_post.server.id.header"),
        "http_post_server_output_header": get(mp, "http_post.server.output.header"),
        # # Works for deeper nested stuff
        # "session_id":      get(mp, "http_get.client.id.parameter"),
        # # Works for top level
        # "jitter":          get(mp, "jitter"),
        # # Handles missing stuff gracefully (returns None)
        # "does_not_exist":  get(mp, "http_get.client.fake_block.garbage")
    }

    for i, j in context.items():
        print(f"{i}:{j}")

    return context


# helper for mc2
def get(obj, path):
    """
    Safely digs into mp.http_get.client...
    Returns the value if found, or None if any step fails.
    """
    try:
        # 1. Walk down the dot path (e.g. "http_get.client.metadata")
        val = functools.reduce(getattr, path.split("."), obj)

        # 2. If it's an Option/Statement object, return .value. Otherwise return the object.
        return val.value if hasattr(val, "value") else val
    except AttributeError:
        return None
