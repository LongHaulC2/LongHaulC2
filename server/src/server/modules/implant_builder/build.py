import functools
import logging
import shutil
import tempfile
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from mpp import *

from ...db.mysql_connector import get_mysql_session
from ...listeners.malc2 import *
from ...modules.mysql_functions import ListenerService, MySQLImplantPayloadService
from .context_generators.http_wininet import generate_http_wininet_context

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


server_logger = logging.getLogger("server")


def build_implant(listener_uuid, variant):
    """
    Function to call to build implant. API calls this.

    Need:
    listener_uuid (this will extract malleablec2, callback_host, callback_port, and listener type)

    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(variant=variant, listener_uuid=listener_uuid)

    server_logger.info("Building implant")

    # lookup listener data
    with get_mysql_session() as session:
        ls = ListenerService(session)
        listener_data = ls.get_by_id(listener_uuid)

        if not listener_data:
            server_logger.error(f"Could not find listener with provided listener_uuid.")
            return

        listener_data = listener_data.to_dict()

        # print(listener_data.keys())
        """
        dict_keys(['listener_uuid', 'listener_host', 'listener_port', 
        'listener_type', 'listener_name', 'listener_notes', 'listener_active', 
        'listener_profile_name', 'listener_profile_contents'])
        """

    # note - difference betwen lsitener type (http) and listenert type for build (http_wininet)
    # OR - less complicated for user, have a "http" listener, then specify which method
    # done - cleint has a field to specfy variant.
    # add in a field to api, and here, for which variant to build/use.

    listener_type = listener_data.get("listener_type")
    listener_host = listener_data.get("listener_host")
    listener_port = listener_data.get("listener_port")
    malleable_c2_profile = listener_data.get("listener_profile_contents")
    # temp
    build_dir = setup_implant_build_enviornment(
        malleable_c2_profile=malleable_c2_profile,  # need to update to pass the full str, not the path now
        listener_type=listener_type,
        callback_host=listener_host,
        callback_port=int(listener_port),
        variant=variant,
    )
    docker_build_implant(build_dir)

    # get built implant... somehow. Could get it from the outdir.
    # Maybe anything that is ".ps1, .exe, .dll, etc. " return as a list, and upload
    # for now, just get anything in output.
    output_dir = build_dir / "output"

    for file_path in output_dir.iterdir():
        if file_path.is_file():

            # 1. Read the raw artifact
            payload_bytes = file_path.read_bytes()

            # 2. Register to Database
            with get_mysql_session() as session:
                service = MySQLImplantPayloadService(session)
                service.register_payload(payload_bytes, listener_uuid)


def setup_implant_build_enviornment(
    malleable_c2_profile,
    listener_type,
    callback_host,
    variant,
    callback_port=0,
) -> Path:

    # temp overwrite for mallc2
    # mc2_path = Path("/home/ubuntu-dev/LongHaulC2/tests/profiles/webbug.profile")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        listener_type=listener_type  # malleable_c2=mc2_path.name
    )
    server_logger.info("Generating implant")

    # The directory is created when entering the block
    with tempfile.TemporaryDirectory(delete=False) as tmp_dir:
        server_logger.debug(f"Creating implant at {tmp_dir}")
        # creat base implant structure
        copy_base_structure(source_dir=IMPLANT_BASE, dest_dir=Path(tmp_dir).resolve())

        # print(f"File created: {temp_file}")
        render_implant(
            output_dir=Path(tmp_dir).resolve(),
            malleable_c2_profile=malleable_c2_profile,
            listener_type=listener_type,
            callback_host=callback_host,
            callback_port=callback_port,
            # protocol_variant = whatever
            variant=variant,
        )
    return Path(tmp_dir)


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

    # Add Listener Specific files, based on variant.
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

        # case "smb_named_pipe":
        #     global_context["protocol"] = "SMB"
        #     files_to_render[OUTPUT_DIR / "comms/transport.cpp"] = (
        #         "protocols/smb/pipe.cpp.j2"
        #     )

        case _:
            raise ValueError(f"Unknown listener type: {listener_type}")

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


def docker_build_implant(source_code_dir: Path):
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(source_dir=str(source_code_dir))

    import docker

    client = docker.from_env()

    source_dir = str(source_code_dir.resolve())
    out_dir = str(source_code_dir.resolve() / "output")

    server_logger.info(f"Build configuration - Source: {source_dir}")
    server_logger.info(f"Build configuration - Output: {out_dir}")

    # The shell command to run inside the container:
    # 1. ls -R /source               -> Debug file placement
    # 2. cmake -S /source -B /build  -> Generate Makefiles
    # 3. cmake --build /build        -> Compile
    # to show all files; ls -R /source &&
    build_cmd = "bash -c 'cmake -S /source -B /build -DCMAKE_BUILD_TYPE=Release && cmake --build /build -- -j$(nproc)'"

    server_logger.info("Spinning up ephemeral container (win_x64)...")

    # ephemeral container build
    container = client.containers.run(
        "win_x64",
        command=build_cmd,
        volumes={
            # note- key is on host, bind is in container
            source_dir: {
                "bind": "/source",
                "mode": "rw",
            },  # temp dir where code is generated
            out_dir: {
                "bind": "/output",
                "mode": "rw",
            },  # temp dir created b4, binary is read out of here.
        },
        # detaches and nukes the container after build. off for debugging for now
        # remove=True,
        detach=True,
    )

    server_logger.info(
        f"Container {container.short_id} started. Waiting for build to finish..."
    )

    # Block and wait for result
    result = container.wait()
    exit_code = result.get("StatusCode", -1)

    # Get logs (stdout + stderr)
    logs = container.logs().decode()

    if exit_code == 0:
        server_logger.info("Docker build completed successfully.")
        # Log full output at debug level to keep main logs clean, unless you want it always visible
        server_logger.debug(f"DOCKER LOGS:\n{logs}")
    else:
        server_logger.error(f"Docker build failed with exit code {exit_code}.")
        server_logger.error(f"DOCKER LOGS:\n{logs}")

    # clean up container object reference (optional if remove=True is uncommented above)
    # container.remove()
