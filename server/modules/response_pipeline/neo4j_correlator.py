import base64
import hashlib

import structlog
from edwh_uuid7 import uuid7

from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLImplantFileService, MySQLImplantTaskService
from ...db.neo4j_functions import (
    Neo4jChainingService,
    Neo4jFileNodeService,
    Neo4jImplantNodeService,
    Neo4jMemstoreFileNodeService,
)

response_pipeline_logger = structlog.getLogger("response_pipeline")
server_logger = structlog.getLogger("server")


def _handle_memstore_upload(task_request_dict: dict, task_response_dict: dict, implant_uuid: str):  # noqa
    # try a local logger and bind to it for this scope
    memstore_upload_logger = response_pipeline_logger.bind(task="memstore upload")
    try:
        file_name = task_request_dict.get("task", {}).get("args", {}).get("file_name", "")
        if not file_name:
            memstore_upload_logger.info("file_name is empty", file_name=file_name)
            return

        file_contents = (
            task_request_dict.get("task", {}).get("args", {}).get("file_contents", "")  # store as bytes in db
        )
        if not file_contents:
            memstore_upload_logger.info("file_contents are empty", file_contents=file_contents)
            return

        decoded_bytes = base64.b64decode(file_contents)
        hash = hashlib.md5(decoded_bytes).hexdigest()

        Neo4jMemstoreFileNodeService.connect_memstore_file_to_implant(
            file_name=file_name, implant_uuid=implant_uuid, file_hash_md5=hash
        )
        # add addtl metadata
        file_node = Neo4jMemstoreFileNodeService.create_or_get_node(file_name)

        # only get first 20 chars
        try:
            # add 0x for preivew/user knows it's hex
            file_node.file_preview = "0x" + decoded_bytes.hex()[:20]
        except Exception as e:
            memstore_upload_logger.error("Error saving file_preview", error=e)

        try:
            # add 0x for preivew/user knows it's hex
            file_node.file_size_kb = len(decoded_bytes) / 1000  # convert to kb
        except Exception as e:
            memstore_upload_logger.error("Error saving file_size_kb", error=e)

        file_node.save()
    except Exception as e:
        memstore_upload_logger.error("An error occurred", error=e)


def _handle_memstore_clear(task_request_dict: dict, task_response_dict: dict, implant_uuid: str):  # noqa
    # remove all file from host
    memstore_clear_logger = response_pipeline_logger.bind(task="memstore clear")
    try:
        # get all files connected to implant
        connected_file_nodes = Neo4jMemstoreFileNodeService.get_all_files_nodes_for_implant(implant_uuid=implant_uuid)
        for node in connected_file_nodes:
            node.delete()

    except Exception as e:
        memstore_clear_logger.error("An error occurred", error=e)


def _handle_memstore_delete(task_request_dict: dict, task_response_dict: dict, implant_uuid: str):  # noqa
    # remove a memstore file from host
    memstore_delete_logger = response_pipeline_logger.bind(task="memstore delete")

    try:
        file_name = task_request_dict.get("task", {}).get("args", {}).get("file_name", "")

        # the one file connected to the implant
        # note - this might create it if it doesn't exist for some reason, just for it to be deleted.
        file_node = Neo4jMemstoreFileNodeService.create_or_get_node(file_name=file_name)
        # and delete it
        if file_node:
            file_node.delete()

    except Exception as e:
        memstore_delete_logger.error("An error occured", error=e)


def _handle_file_upload(task_request_dict: dict, task_response_dict: dict, implant_uuid: str):  # noqa
    # get file name, contents, path
    # add node
    file_upload_logger = response_pipeline_logger.bind(task="file upload")

    try:
        file_path = task_request_dict.get("task", {}).get("args", {}).get("file_path", "")

        file_contents = (
            task_request_dict.get("task", {}).get("args", {}).get("file_contents", "")  # store as bytes in db
        )

        host_node = Neo4jImplantNodeService.get_host_implant_is_connected_to(implant_uuid)

        if not host_node:
            response_pipeline_logger.error("Could not find host that implant is connected to")
            return

        hostname = host_node.hostname

        decoded_bytes = base64.b64decode(file_contents)
        hash = hashlib.md5(decoded_bytes).hexdigest()

        Neo4jFileNodeService.connect_file_to_host(file_path=file_path, hostname=hostname, file_hash_md5=hash)

        # addtl metadata
        file_node = Neo4jFileNodeService.create_or_get_node(file_path)

        try:
            # add 0x for preivew/user knows it's hex
            file_node.file_preview = "0x" + decoded_bytes.hex()[:20]
        except Exception as e:
            response_pipeline_logger.error("Error saving file_preview", error=e)

        try:
            # add 0x for preivew/user knows it's hex
            file_node.file_size_kb = len(decoded_bytes) / 1000  # convert to kb
        except Exception as e:
            response_pipeline_logger.error("Error saving file_size_kb", error=e)

        file_node.save()
    except Exception as e:
        file_upload_logger.error("An error occured", error=e)

    # # I don't have a file delete, damn.
    # case "file delete":
    #     file_name = task_request_dict.get("task", {}).get("args", {}).get("file_name", "")

    #     # the one file connected to the implant
    #     # note - this might create it if it doesn't exist for some reason, just for it to be deleted.
    #     file_node = Neo4jFileNodeService.create_or_get_node(file_name=file_name)
    #     # and delete it
    #     if file_node:
    #         file_node.delete()

    # could do a file clear, that attempts to nuke all files, which would use the get_all_files_nodes_for_host


def _handle_file_download(task_request_dict: dict, task_response_dict: dict, implant_uuid: str):  # noqa
    file_download_logger = response_pipeline_logger.bind(task="file download")
    try:
        file_path = task_request_dict.get("task", {}).get("args", {}).get("file_path", "")
        file_data = task_response_dict.get("result", {}).get("data", b"")

        if not file_data:
            file_download_logger.info("No file data in response")
            return

        # Data arrives as bytes for binary files (invalid UTF-8 survived _decode_bytes
        # in handle_exfil) or as str for text files (valid UTF-8 got decoded). The
        # implant sends raw content, never base64 — so str is re-encoded, not decoded.
        if isinstance(file_data, str):
            file_bytes = file_data.encode("utf-8")
        elif isinstance(file_data, list | bytearray):
            file_bytes = bytes(file_data)
        else:
            file_bytes = file_data

        if not file_bytes:
            return

        file_name = file_path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] or "unknown_download"
        file_uuid = str(uuid7())

        with get_mysql_session() as session:
            file_service = MySQLImplantFileService(session)
            file_service.register_file(
                file_name=file_name,
                file_bytes=file_bytes,
                file_uuid=file_uuid,
                uploaded_by=f"implant:{implant_uuid}",
                source_implant=implant_uuid,
            )

        file_download_logger.info(
            "Auto-captured downloaded file to filestore",
            file_name=file_name,
            file_uuid=file_uuid,
            size_bytes=len(file_bytes),
        )
    except Exception as e:
        file_download_logger.error("Failed to auto-capture downloaded file", error=e)


def _handle_smb_link(task_request_dict: dict, task_response_dict: dict, implant_uuid: str):  # noqa
    """
    Link actions.

    If our link is successful,
    - create or get child node by child_uuid
    - add relationship of CHILD_OF (to parent)

    - create or get parent node by implant_uuid
    - add relationship of PARENT_TO (child)

    This should be enough for querying parent/child rel's
    """
    link_logger = response_pipeline_logger.bind(task="link")
    try:
        child_uuid = task_response_dict.get("result", {}).get("data", {}).get("child_uuid", "")
        # parent_uuid = task_request_dict.get("task", {}).get("args", {}).get("implant_uuid", "")
        parent_uuid = implant_uuid

        if not child_uuid:
            link_logger.error("Child uuid empty")
            return

        if not parent_uuid:
            link_logger.error("Parent uuid empty")
            return

        # create parent -> child,
        Neo4jChainingService.link_child_to_parent_node(child_uuid=child_uuid, parent_uuid=parent_uuid)
    except Exception as e:
        link_logger.error("An error occured", error=e)


TASK_HANDLERS = {
    "memstore upload": _handle_memstore_upload,
    "memstore clear": _handle_memstore_clear,
    "memstore delete": _handle_memstore_delete,
    "file upload": _handle_file_upload,
    "file download": _handle_file_download,
    "link smb": _handle_smb_link,
}


def correlate_task_results(task_response_dict: dict):
    # response_pipeline_logger.critical("IT IS WORKING")
    task_uuid = task_response_dict.get("task_uuid", "")
    implant_uuid = task_response_dict.get("implant_uuid")

    if not task_uuid:
        response_pipeline_logger.warning("Task response did not have a task_uuid")
        return

    if not implant_uuid:
        response_pipeline_logger.warning("Task response did not have a implant_uuid")
        return

    # get full task from DB
    task_request_dict = {}
    with get_mysql_session() as session:
        task = MySQLImplantTaskService(implant_uuid=implant_uuid, session=session)
        # fyi - this returns the full task: task_request, task_response, implant_uuid, task_uuid.
        # Need to pull out task request
        task_dict = task.get_task_by_uuid(task_uuid)

    if not task_dict:
        response_pipeline_logger.warning("Task lookup did not yield any data")
        return

    # filter down to task_request
    task_request_dict = task_dict.get("task_request", {})
    task_name = task_request_dict.get("task", {}).get("task_name", "")

    # check if task was successful. If not, return.
    windows_error_code = task_response_dict.get("result", {}).get("windows_error_code", "")
    if windows_error_code != 0:
        response_pipeline_logger.warning(
            "Task Result was not successful. Not updating Neo4j",
            windows_error_code=windows_error_code,
        )
        return

    # based off task name, do neo4j actions
    handler_func = TASK_HANDLERS.get(task_name)

    if handler_func:
        handler_func(task_request_dict, task_response_dict, implant_uuid)
    else:
        # Logging for when a new task type is processed but doesn't have a Neo4j routine
        response_pipeline_logger.debug("No specific Neo4j handler for this task", task_name=task_name)
