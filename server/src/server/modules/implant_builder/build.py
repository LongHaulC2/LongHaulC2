import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Union

import docker
import structlog
from mpp import MalleableProfile

from ...db.mysql_connector import get_mysql_session
from ...listeners.malc2 import *
from ...modules.mysql_functions import ListenerService, MySQLImplantPayloadService
from .render import render_file, render_implant

# this file, up one dir, to implant_base
IMPLANT_BASE = Path(__file__).parent / "implant_base"

server_logger = logging.getLogger("server")


def build_implant(implant_name, listener_uuid, variant, output_format):
    """
    Function to call to build implant. API calls this.

    Need:
    listener_uuid (this will extract malleablec2, callback_host, callback_port, and listener type)

    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(variant=variant, listener_uuid=listener_uuid)

    server_logger.info("Building implant")
    server_logger.warning(
        "WARNING: Output Format passed in, but not yet imlemented. .EXE only right now"
    )

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

    # setup build enviornment, creates a temp dir in /tmp/...
    build_dir = setup_implant_build_enviornment(
        malleable_c2_profile=malleable_c2_profile,
        listener_type=listener_type,
        callback_host=listener_host,
        callback_port=int(listener_port),
        variant=variant,
    )
    # built the implant with docker
    docker_build_implant(build_dir)
    # and store in DB
    store_data_post_build(
        build_dir=build_dir, payload_name=implant_name, listener_uuid=listener_uuid
    )


def store_data_post_build(
    build_dir: Union[str, Path], payload_name: str, listener_uuid: str
) -> None:
    """
    Zips the source code from the build directory and uploads build artifacts
    (payloads) to the database.
    """
    build_path = Path(build_dir)

    # Checks
    if not build_path.exists():
        server_logger.error(f"Build failed: Directory not found at {build_path}")
        return

    server_logger.info(f"Starting post-build storage for implant: {payload_name}")

    try:
        # Zip Source Code
        zip_location = build_path / f"{payload_name}_source.zip"
        server_logger.debug(f"Zipping source code to {zip_location}")

        with zipfile.ZipFile(zip_location, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for path in build_path.rglob("*"):
                # Don't zip the zip file itself if it's in the same dir
                if path.resolve() == zip_location.resolve():
                    continue

                if path.is_file():
                    z.write(path, arcname=path.relative_to(build_path))

        # Get zip contetns
        zip_bytes = zip_location.read_bytes()
        server_logger.debug(f"Source zipped successfully ({len(zip_bytes)} bytes).")

    except Exception as e:
        server_logger.error(f"Failed to zip source code for {payload_name}: {e}")
        return

    # Process Build Artifacts
    output_dir = build_path / "output"

    if not output_dir.exists():
        server_logger.warning(
            f"No 'output' directory found in {build_path}. Skipping artifact upload."
        )
        return

    # Get list of artifacts (filtering out directories) - may need to do a filter for .exe, dll, etc - but for now it saves all of them
    artifacts = [p for p in output_dir.iterdir() if p.is_file()]

    if not artifacts:
        server_logger.warning(
            f"Output directory exists but contains no files: {output_dir}"
        )
        return
    server_logger.info(f"Found {len(artifacts)} artifact(s) to upload.")

    # write to db
    try:
        with get_mysql_session() as session:
            service = MySQLImplantPayloadService(session)

            for file_path in artifacts:
                try:
                    payload_bytes = file_path.read_bytes()

                    server_logger.debug(f"Registering payload: {file_path.name}")

                    service.register_payload(
                        payload_name=payload_name,
                        payload_bytes=payload_bytes,
                        listener_uuid=listener_uuid,
                        source_code_bytes=zip_bytes,
                    )
                except Exception as file_error:
                    server_logger.error(
                        f"Failed to read or register specific artifact {file_path.name}: {file_error}"
                    )
                    continue

        server_logger.info(f"Successfully registered artifacts for {payload_name}.")

    except Exception as db_error:
        server_logger.error(
            f"Database transaction failed for {payload_name}: {db_error}"
        )


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


def copy_file(source: Path, dest: Path):
    """
    Copies a file from source to dest, ensuring the destination directory exists.
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(source=source, dest=dest)
    server_logger.debug(f"Copying file")

    # Sanity Check
    if not source.exists():
        server_logger.error(f"Error: Source file missing: {source}")
        return

    # create the folder structure if it doesn't exist
    # (e.g., if dest is 'build/libs/core.lib', this makes 'build/libs/')
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        # copy2 preserves metadata like timestamps
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
        remove=True,
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
