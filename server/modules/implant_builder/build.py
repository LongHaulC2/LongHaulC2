import json
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

import docker
import structlog
from docker.models.containers import Container

from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLArtifactService, MySQLImplantPayloadService
from ...db.neo4j_functions import Neo4jListenerNodeService
from ..template_manager.manager import TemplateManager
from .render import materialize_modules, render_implant, sanitize_cpp_name
from .types import ListenerProfile

server_logger = structlog.getLogger("server")
docker_logger = structlog.getLogger("docker_logger")


def build_implant(
    implant_name: str,
    listener_uuids: list,
    build_uuid: str,
    init_get_profile_listener_uuid: str,
    init_post_profile_listener_uuid: str,
    callback_host: str | None = None,
    options: dict | None = None,
    template_name: str = "win_x64",
    modules: list[str] | None = None,
) -> dict:
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(build_uuid=build_uuid, implant_name=implant_name)
    server_logger.info("Starting implant build process")

    # init inside of func to avoid mutable as default problems with python
    if options is None:
        options = {}

    build_stats = {"build_time": 0.0}

    template_info = TemplateManager.get_by_name(template_name)
    if not template_info:
        server_logger.error("Template not found", template_name=template_name)
        return build_stats
    template_dir = TemplateManager.get_template_dir(template_name)

    if modules is None:
        modules = template_info.get("build", {}).get("default_modules", [])

    docker_image = template_info.get("docker_image", template_name)

    modules = _ensure_required_modules(modules)

    module_bundles = _fetch_module_bundles(modules)
    if module_bundles is None:
        server_logger.error("Failed to fetch modules from DB")
        return build_stats

    full_listeners_data: dict[str, ListenerProfile] = {}
    start_time = time.perf_counter()

    with get_mysql_session() as session:
        listener_service = Neo4jListenerNodeService()
        payload_service = MySQLImplantPayloadService(session)

        # Register build start
        payload_service.register_build_start(
            payload_name=implant_name,
            build_uuid=build_uuid,
            listener_uuids=listener_uuids,
        )
        payload_service.update_build_status(build_uuid=build_uuid, build_status="building")

        try:
            for uuid in listener_uuids:
                # Fetch full details from DB of the listener to include
                db_listener = listener_service.get_by_id(uuid)

                if not db_listener:
                    server_logger.error("Listener not found.", listener_uuid=uuid)
                    raise ValueError(f"Invalid listener UUID: {uuid}")

                listener_data = db_listener.to_dict()

                if not listener_data.get("listener_profile_contents"):
                    server_logger.error(
                        "Listener has no profile configured — cannot build",
                        listener_uuid=uuid,
                        listener_name=listener_data.get("listener_name"),
                    )
                    raise ValueError(f"Listener {uuid} has no profile contents. Assign a profile before building.")

                listener_data["listener_profile_name"] = sanitize_cpp_name(listener_data["listener_name"])

                full_listeners_data[uuid] = listener_data

        except Exception as e:
            server_logger.error("Failed to prepare listener data", error=e)
            payload_service.update_build_status(build_uuid=build_uuid, build_status="failed")
            return None

    # check if /dev/shm (ramdisk) is available, for faster access overall
    # I've found /dev/shm to give 1-2 second decrease in build times overall.
    shm = Path("/dev/shm")
    # ! Check for write perms, as well as existence of /dev/shm.
    base_tmp = str(shm) if shm.exists() and os.access(shm, os.W_OK) else "/tmp"

    # Build Environment & Logic
    # ! delete=False is intentional. tempfile nukes the directory before it's done being used, resulting in a
    # ! "failed" build, as the binary & source are never written back to the DB, because they don't exist.
    with tempfile.TemporaryDirectory(delete=False, dir=base_tmp) as tmp_dir_str:
        build_dir = Path(tmp_dir_str).resolve()

        try:
            _generate_source_code(
                build_dir=build_dir,
                template_dir=template_dir,
                listeners=full_listeners_data,
                init_get_uuid=init_get_profile_listener_uuid,
                init_post_uuid=init_post_profile_listener_uuid,
                callback_host=callback_host,
                module_bundles=module_bundles,
            )

            if _run_docker_build(build_dir, docker_image=docker_image, options=options):
                _store_artifacts(build_dir, implant_name, build_uuid, listener_uuids)

            else:
                raise RuntimeError("Compilation failed")

        except Exception:
            server_logger.exception("Build failed")
            with get_mysql_session() as session:
                MySQLImplantPayloadService(session).update_build_status(build_uuid=build_uuid, build_status="failed")

        finally:
            if build_dir.exists():
                shutil.rmtree(build_dir, ignore_errors=True)
            # _nuke_old_builds(str(build_dir))
            build_time = time.perf_counter() - start_time
            build_stats["build_time"] = build_time

    return build_stats


def _ensure_required_modules(modules: list[str]) -> list[str]:
    from ...db.mysql_models import ArtifactStore

    with get_mysql_session() as session:
        all_artifacts = session.query(ArtifactStore).filter_by(artifact_type="module").all()
        for artifact in all_artifacts:
            try:
                bundle = json.loads(artifact.artifact_contents)
                mod_info = bundle.get("module", {})
                name = mod_info.get("name", "")
                if not mod_info.get("removable", True) and name not in modules:
                    server_logger.info("Auto-including required module", module_name=name)
                    modules.append(name)
            except json.JSONDecodeError:
                continue
    return modules


def _fetch_module_bundles(module_names: list[str]) -> list[dict] | None:
    bundles = []
    with get_mysql_session() as session:
        service = MySQLArtifactService(session)
        for name in module_names:
            artifact = service.get_artifact_by_name("module", name)
            if not artifact:
                server_logger.error("Module not found in DB", module_name=name)
                return None
            try:
                bundle = json.loads(artifact.artifact_contents)
                bundles.append(bundle)
            except json.JSONDecodeError:
                server_logger.error("Invalid JSON in module", module_name=name)
                return None
    return bundles


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
    template_dir: Path,
    listeners: dict[str, ListenerProfile],
    init_get_uuid: str,
    init_post_uuid: str,
    callback_host: str | None = None,
    module_bundles: list[dict] | None = None,
):
    server_logger.debug("Generating source code", build_dir=build_dir, template=template_dir.name)

    if not template_dir.exists():
        raise FileNotFoundError(f"Template not found at {template_dir}")
    shutil.copytree(template_dir, build_dir, dirs_exist_ok=True, copy_function=shutil.copy2)

    if module_bundles:
        materialize_modules(build_dir, module_bundles)

    render_implant(
        output_dir=build_dir,
        template_dir=template_dir,
        listeners_data_dict=listeners,
        initial_get_profile_listener_uuid=init_get_uuid,
        initial_post_profile_listener_uuid=init_post_uuid,
        callback_host=callback_host,
        enabled_modules=module_bundles,
    )


def _run_docker_build(build_dir: Path, docker_image: str = "win_x64", options: dict | None = None) -> bool:
    """Runs the compilation container."""
    if options is None:
        options = {}
    client = docker.from_env()

    docker_logger.info("Build Dir:", build_dir=build_dir)

    base_dir = Path(build_dir).parent
    persistent_build_dir = Path(base_dir) / "build"

    if options.get("clear_cache", False):
        docker_logger.info("Clearing previous build artifacts & cache")
        shutil.rmtree(str(persistent_build_dir), ignore_errors=True)

    persistent_build_dir.mkdir(parents=True, exist_ok=True)

    debug_requested = options.get("debug", False)
    cmake_debug_flag = "-DENABLE_IMPLANT_LOGS=ON" if debug_requested else "-DENABLE_IMPLANT_LOGS=OFF"
    cmd = (
        f"bash -c 'cmake -G Ninja -S /source -B /build -DCMAKE_BUILD_TYPE=Release {cmake_debug_flag} && "
        "ninja -C /build && chmod -R 777 /source /output /build'"
    )

    docker_logger.info("Spinning up builder container", image=docker_image)

    volumes = {
        str(build_dir): {"bind": "/source", "mode": "rw"},
        str(build_dir / "output"): {"bind": "/output", "mode": "rw"},
        str(persistent_build_dir): {"bind": "/build", "mode": "rw"},
    }

    try:
        container: Container = client.containers.run(
            docker_image,
            command=cmd,
            volumes=volumes,
            detach=True,
        )

        # Wait for finish
        result = container.wait()
        logs = container.logs().decode()
        exit_code = result.get("StatusCode", -1)

        # Cleanup container immediately
        container.remove()

        if exit_code == 0:
            docker_logger.debug("Docker Build Success", logs=logs)
            return True
        docker_logger.error("Docker Build Failed", exit_code=exit_code, logs=logs)
        return False

    except Exception as e:
        docker_logger.error("Docker infrastructure error", error=e)
        return False


# def _store_artifacts(build_dir: Path, implant_name: str, build_uuid: str):
#     """Zips source and uploads binaries to DB."""
#     output_dir = build_dir / "output"
#     zip_path = build_dir / f"{implant_name}_source.zip"

#     # zip up the source code
#     with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
#         for path in build_dir.rglob("*"):
#             if path.is_file() and path != zip_path and "output" not in path.parts:
#                 z.write(path, arcname=path.relative_to(build_dir))

#     zip_bytes = zip_path.read_bytes()

#     # grab list of artifacts
#     artifacts = [p for p in output_dir.iterdir() if p.is_file()]
#     if not artifacts:
#         server_logger.warning("No artifacts found in output directory.")
#         return

#     # write payload to db
#     with get_mysql_session() as session:
#         service = MySQLImplantPayloadService(session)
#         for artifact in artifacts:
#             service.register_payload(
#                 payload_name=implant_name,
#                 payload_bytes=artifact.read_bytes(),
#                 source_code_bytes=zip_bytes,
#                 # listener_uuid=primary_listener_uuid,
#                 build_uuid=build_uuid,
#             )

#         # Update the build status to complete/success
#         service.update_build_status(build_uuid=build_uuid, build_status="complete")

#     server_logger.info("Stored artifacts", number_of_artifacts=len(artifacts), implant_name=implant_name)


# updated to store multiple artifacts
def _store_artifacts(build_dir: Path, implant_name: str, build_uuid: str, listener_uuids: list | None = None):
    """Zips source and uploads individual binary artifacts to DB."""
    output_dir = build_dir / "output"
    zip_path = build_dir / f"{implant_name}_source.zip"

    # sanity check output cuz of exe/dll bug
    if output_dir.exists():
        # Grab just the file/folder names to keep the log clean
        found_items = [p.name for p in output_dir.iterdir()]
        docker_logger.warning("Post-build output directory contents", output_path=str(output_dir), items=found_items)

    # Zip up the source code
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in build_dir.rglob("*"):
            if path.is_file() and path != zip_path and "output" not in path.parts:
                z.write(path, arcname=path.relative_to(build_dir))

    zip_bytes = zip_path.read_bytes()

    # Grab list of artifacts, filtering for valid extensions - which are currently .exe & .dll
    valid_extensions = {".exe", ".dll"}
    artifacts = [p for p in output_dir.iterdir() if p.is_file() and p.suffix.lower() in valid_extensions]

    if not artifacts:
        server_logger.warning("No valid artifacts (.exe, .dll) found in output directory.")
        # could set build to failed as well if there's nothign here
        return

    # Write each payload to the DB
    with get_mysql_session() as session:
        service = MySQLImplantPayloadService(session)
        for artifact in artifacts:
            # Differentiate the payload name in the DB (ex "my_implant.exe" and "my_implant.dll")
            artifact_db_name = f"{implant_name}{artifact.suffix}"

            service.register_payload(
                payload_name=artifact_db_name,
                payload_bytes=artifact.read_bytes(),
                source_code_bytes=zip_bytes,
                build_uuid=build_uuid,
                listener_uuids=listener_uuids,
            )
            server_logger.debug("Stored individual artifact", artifact_name=artifact.name)

        # Update the build status to complete/success after all are written
        service.update_build_status(build_uuid=build_uuid, build_status="complete")

    server_logger.info("Stored artifacts successfully", number_of_artifacts=len(artifacts), implant_name=implant_name)
