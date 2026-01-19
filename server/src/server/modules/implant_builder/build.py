import logging
import shutil
import tempfile
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from mpp import *

from ...listeners.malc2 import *
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

import functools

server_logger = logging.getLogger("server")


def build_implant(listener_uuid):
    """
    Function to call to build implant. API calls this.

    Need:
    listener_uuid (this will extract malleablec2, callback_host, callback_port, and listener type)

    """

    # lookup listener data

    # temp
    mc2_path = Path("/home/ubuntu-dev/LongHaulC2/tests/profiles/webbug.profile")
    build_dir = create_implant(
        malleable_c2_path=mc2_path,
        listener_type="http_wininet",
        callback_host="0.0.0.0",
        callback_port=9010,
    )
    docker_build_implant(build_dir)

    # get built implant

    # write to db


def create_implant(
    malleable_c2_path, listener_type, callback_host, callback_port=0
) -> Path:

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
            callback_host=callback_host,
            callback_port=callback_port,
        )
    return Path(tmp_dir)


def _create_implant(
    output_dir: Path, malleable_c2_path, listener_type, callback_host, callback_port
):

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        output_dir=output_dir,
        malleable_c2_path=malleable_c2_path,
        listener_type=listener_type,
    )
    server_logger.debug("_create_implant")

    # 1. Generate the shared context (Data usually needed by ALL files)
    # these are the keys that get plugged into the templates
    # one per listener type for explicitness/control
    match listener_type:
        case "http_wininet":
            global_context = generate_http_wininet_context(
                malleable_c2_path, callback_host, callback_port
            )

        case _:
            server_logger.error(f"Invalid listener type: {listener_type}")
            return

    # 2. Define the File Map
    # Structure: "Destination Path" : "Source Template"
    files_to_render = {}

    # Add Listener Specific files
    match listener_type:
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
    import docker

    client = docker.from_env()

    source_dir = str(source_code_dir.resolve())
    out_dir = str(source_code_dir.resolve() / "output")

    print(source_dir)
    print(out_dir)

    # The shell command to run inside the container:
    # 1. cmake -S /source -B /build  -> Generate Makefiles from /source into /build
    # 2. cmake --build /build        -> Compile the code
    build_cmd = "bash -c 'ls -R /source && cmake -S /source -B /build -DCMAKE_BUILD_TYPE=Release && cmake --build /build -- -j$(nproc)'"

    # ephemeral container build
    container = client.containers.run(
        "win_x64",
        command=build_cmd,  # "ls -lsa /source",
        volumes={
            # note- key is on host, bind is in container
            source_dir: {
                "bind": "/source",
                "mode": "rw",
            },  # temp dir where code is generated
            out_dir: {
                "bind": "/output",
                "mode": "rw",
            },  # temp dir ccreated b4, binary is read out of here.
        },
        # detacehs and nukes the container after build
        # remove=True,
        detach=True,
    )
    container.wait()

    # view mounts
    # print(container.attrs['Mounts'])

    # Get logs (stdout + stderr)
    logs = container.logs()  # returns bytes
    print("DOCKER LOGS")
    print(logs.decode())
