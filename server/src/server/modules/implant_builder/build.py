import shutil
import tempfile
import zipfile
from pathlib import Path

import docker
import structlog
from docker.models.containers import Container

# Import your DB modules here...
from ...db.mysql_connector import get_mysql_session
from ...modules.mysql_functions import ListenerService, MySQLImplantPayloadService
from .render import render_implant, sanitize_cpp_name
from .types import ListenerProfile

IMPLANT_BASE = Path(__file__).parent / "implant_base"
server_logger = structlog.getLogger("server")


def build_implant(
    implant_name: str,
    # this is the API data that is sent in. We use data from here to get the rest of the listener data.
    listener_uuids: list,
    build_uuid: str,
    init_get_profile_listener_uuid: str,
    init_post_profile_listener_uuid: str,
) -> None:
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(build_uuid=build_uuid, implant_name=implant_name)
    server_logger.info("Starting implant build process")

    # Get full listener data from DB
    full_listeners_data: dict[str, ListenerProfile] = {}

    with get_mysql_session() as session:
        listener_service = ListenerService(session)
        payload_service = MySQLImplantPayloadService(session)

        # Register build start
        payload_service.register_build_start(
            payload_name=implant_name,
            build_uuid=build_uuid,
        )
        payload_service.update_build_status(build_uuid=build_uuid, build_status="building")

        try:
            for uuid in listener_uuids:
                # Fetch full details from DB of the listener to include
                db_listener = listener_service.get_by_id(uuid)

                if not db_listener:
                    server_logger.error("Listener not found.", listener_uuid=uuid)
                    raise ValueError(f"Invalid listener UUID: {uuid}")

                # snag and sanitize the name of that listeenr
                listener_data = db_listener.to_dict()
                listener_data["listener_profile_name"] = sanitize_cpp_name(listener_data["listener_name"])

                # Store data for the renderer
                full_listeners_data[uuid] = listener_data

        except Exception as e:
            server_logger.error("Failed to prepare listener data", error=e)
            payload_service.update_build_status(build_uuid=build_uuid, build_status="failed")
            return

    # Build Environment & Logic (Now using full_listeners_data)
    with tempfile.TemporaryDirectory(delete=False) as tmp_dir_str:
        build_dir = Path(tmp_dir_str).resolve()

        try:
            # Generate Source
            _generate_source_code(
                build_dir=build_dir,
                listeners=full_listeners_data,
                init_get_uuid=init_get_profile_listener_uuid,
                init_post_uuid=init_post_profile_listener_uuid,
            )

            # Compile
            if _run_docker_build(build_dir):
                _store_artifacts(build_dir, implant_name, build_uuid)
            else:
                raise RuntimeError("Compilation failed")

        except Exception:
            server_logger.exception("Build failed")
            with get_mysql_session() as session:
                MySQLImplantPayloadService(session).update_build_status(build_uuid=build_uuid, build_status="failed")


def _prepare_listener_data(
    raw_listeners: dict[str, dict],
) -> dict[str, ListenerProfile]:
    """Sanitizes names and validates structure before processing."""
    clean_listeners = {}
    for uuid, data in raw_listeners.items():
        data["listener_profile_name"] = sanitize_cpp_name(data.get("listener_profile_name", "default"))
        clean_listeners[uuid] = data
    return clean_listeners


def _generate_source_code(
    build_dir: Path,
    listeners: dict[str, ListenerProfile],
    init_get_uuid: str,
    init_post_uuid: str,
):
    """Copies base structure and renders templates."""
    server_logger.debug("Generating source code", build_dir=build_dir)

    # Copy base
    if not IMPLANT_BASE.exists():
        raise FileNotFoundError(f"Implant base not found at {IMPLANT_BASE}")
    shutil.copytree(IMPLANT_BASE, build_dir, dirs_exist_ok=True)

    # Render Jinja
    render_implant(
        output_dir=build_dir,
        listeners_data_dict=listeners,
        initial_get_profile_listener_uuid=init_get_uuid,
        initial_post_profile_listener_uuid=init_post_uuid,
    )


def _run_docker_build(build_dir: Path) -> bool:
    """Runs the compilation container."""
    client = docker.from_env()
    source_vol = str(build_dir)
    output_vol = str(build_dir / "output")

    # Command: CMake configure -> CMake build
    # -j$(nproc) uses all cores
    cmd = "bash -c 'cmake -S /source -B /build -DCMAKE_BUILD_TYPE=Release && cmake --build /build -- -j$(nproc)'"

    server_logger.info("Spinning up builder container (win_x64)")

    try:
        container: Container = client.containers.run(
            "win_x64",
            command=cmd,
            volumes={
                source_vol: {"bind": "/source", "mode": "rw"},
                output_vol: {"bind": "/output", "mode": "rw"},
            },
            detach=True,
        )

        # Wait for finish
        result = container.wait()
        logs = container.logs().decode()
        exit_code = result.get("StatusCode", -1)

        # Cleanup container immediately
        container.remove()

        if exit_code == 0:
            server_logger.debug("Docker Build Success", logs=logs)
            return True
        else:
            server_logger.error("Docker Build Failed", exit_code=exit_code, logs=logs)
            return False

    except Exception as e:
        server_logger.error("Docker infrastructure error", error=e)
        return False


def _store_artifacts(build_dir: Path, implant_name: str, build_uuid: str):
    """Zips source and uploads binaries to DB."""
    output_dir = build_dir / "output"
    zip_path = build_dir / f"{implant_name}_source.zip"

    # zip up the source code
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in build_dir.rglob("*"):
            if path.is_file() and path != zip_path and "output" not in path.parts:
                z.write(path, arcname=path.relative_to(build_dir))

    zip_bytes = zip_path.read_bytes()

    # grab list of artifacts
    artifacts = [p for p in output_dir.iterdir() if p.is_file()]
    if not artifacts:
        server_logger.warning("No artifacts found in output directory.")
        return

    # write payload to db
    with get_mysql_session() as session:
        service = MySQLImplantPayloadService(session)
        for artifact in artifacts:
            service.register_payload(
                payload_name=implant_name,
                payload_bytes=artifact.read_bytes(),
                source_code_bytes=zip_bytes,
                # listener_uuid=primary_listener_uuid,
                build_uuid=build_uuid,
            )

        # Update the build status to complete/success
        service.update_build_status(build_uuid=build_uuid, build_status="complete")

    server_logger.info("Stored artifacts", number_of_artifacts=len(artifacts), implant_name=implant_name)
