"""
response_pipeline:

Arguably the cornerstone of this whole project, the response pipeline is responsible for handling responses *from* redis, to where they need to go.

This includes:
 - Writing to MYSQL for retrieval by the GUI
 - Passing responses to neo4j logic to update said relationships there.

"""

# note for performance metrics, the most "efficent" way may be dumping to redis, or using direct metric libs like prometheus, isntead of doing a custom metrics system

import base64
import concurrent.futures
import hashlib
import logging
import threading
import time

import msgpack

from ...db.mysql_connector import get_mysql_session
from ...db.neo4j_models import Neo4jHostNode, Neo4jImplantNode
from ...modules.neo4j_functions import (
    Neo4jFileNodeService,
    Neo4jHostNodeService,
    Neo4jMemstoreFileNodeService,
    Neo4jNetworkNodeService,
    Neo4jNicNodeService,
)
from ..mysql_functions import MySQLImplantTaskService
from ..neo4j_functions import Neo4jImplantNodeService
from ..redis_functions import RedisImplantTaskService

response_pipeline_logger = logging.getLogger("response_pipeline")
server_logger = logging.getLogger("server")


def start_task_batch_job():
    # log this explicity with server main logger
    server_logger.info("Starting task watchdog")
    t = threading.Thread(target=_task_batch_job, daemon=True)
    t.start()


def _task_batch_job():
    response_pipeline_logger.info("Starting task batch job")

    # get our context outside of the thread so we don't re-setup the executor var a bazilliion times
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        while True:
            try:
                # one sessino a loop to prevent stale session issues.

                unpacked_responses_list = []

                # get all implants at time of loop (could cache this in the future, or only go based on redis keys, but for now it's easier to get all of them to check)
                implants = (
                    Neo4jImplantNodeService.get_all()
                )  # ImplantService(session).get_all()

                future_to_implant = {
                    executor.submit(
                        _get_tasks_from_redis_and_write_to_mysql, implant
                    ): implant
                    for implant in implants
                }

                for future in concurrent.futures.as_completed(future_to_implant):
                    try:
                        responses = future.result()
                        if responses:
                            unpacked_responses_list.extend(responses)
                    except Exception as e:
                        response_pipeline_logger.error(f"Thread error: {e}")

                # Neo4j placeholder
                if unpacked_responses_list:
                    for response in unpacked_responses_list:
                        process_single_response_for_neo4j(response)
                    # _neo4j_placeholder(response_list=unpacked_responses_list)

                time.sleep(1)

            except Exception as e:
                response_pipeline_logger.critical(
                    f"Global error in task batch job: {e}"
                )
                time.sleep(1)


def _get_tasks_from_redis_and_write_to_mysql(implant) -> list:
    """
    Atomically moves tasks from Redis to MySQL for a single implant.

    note, using raw redis queries. Put them in redis_functions.py later.
    """
    implant_uuid = implant.get("implant_uuid", "")
    if not implant_uuid:
        response_pipeline_logger.warning("Implant uuid blank")
        return []

    rits = RedisImplantTaskService(implant_uuid)

    # peek data, don't pop as we could lose it then.
    raw_responses = rits.redis.lrange(rits.inbox_key, 0, -1)

    if not raw_responses:
        return []

    # Convert from messagepack to dict
    responses_to_insert = []
    for packed in raw_responses:
        try:
            data = msgpack.unpackb(packed, raw=False)
            responses_to_insert.append(data)
        except Exception as e:
            response_pipeline_logger.error(
                f"Failed to unpack msgpack for {implant_uuid}: {e}"
            )

    if not responses_to_insert:
        # Queue had data, but it was all corrupt. Clear it so we don't loop forever.
        rits.redis.ltrim(rits.inbox_key, len(raw_responses), -1)
        return []

    #  Write to MySQL
    with get_mysql_session() as session:
        try:
            msits = MySQLImplantTaskService(
                implant_uuid=implant_uuid,
                session=session,
            )
            # write all responses at once to not pound the db
            msits.bulk_update_responses(responses=responses_to_insert)
            session.commit()

            # nuke old redis entries, ltrim trims to start,end, so if we had 4 entries that we processed above, 0,1,2,3 would be popped, and the value in 4 would be moved to 0.
            # This makes it okay to have new entries come in, and they don't get deleted as we only trim the number we processed.
            rits.redis.ltrim(rits.inbox_key, len(raw_responses), -1)

            if len(responses_to_insert) > 0:
                response_pipeline_logger.debug(
                    f"Synced {len(responses_to_insert)} tasks for {implant_uuid}"
                )

            # finally, return the responses that were inserted, to the parent for addtl handling
            return responses_to_insert

        except Exception as e:
            session.rollback()
            response_pipeline_logger.error(f"DB Write failed for {implant_uuid}: {e}")
            return []


# def _neo4j_placeholder(response_list: list):
#     response_pipeline_logger.debug(f"neo4j placeholder: list len: {len(response_list)}")

#     # rough idea
#     """
#     For each implant response, pull out ID.

#     if uuid not in neo4j, add to neo4j

#     then do tree

#     lookup_task_id
#     if task_id.task == link:
#         figure out what parent is, what child is, get nodes for each, link in neo4j

#     """
#     ...


def process_single_response_for_neo4j(task_response_dict: dict):
    # response_pipeline_logger.critical("IT IS WORKING")
    task_uuid = task_response_dict.get("task_uuid", "")
    implant_uuid = task_response_dict.get("implant_uuid")

    if not task_uuid:
        response_pipeline_logger.warning("Task response did not have a task_uuid")
        return

    if not implant_uuid:
        response_pipeline_logger.warning("Task response did not have a implant_uuid")
        return

    # need to look this up
    # probably a major choke point if DB is slow. Threading may help
    # task_name = task_dict.get("task_name")

    task_request_dict = {}
    with get_mysql_session() as session:
        task = MySQLImplantTaskService(implant_uuid=implant_uuid, session=session)
        # task_name = task.get(task_name)

        # fyi - this returns the full task: task_request, task_response, implant_uuid, task_uuid.
        # Need to pull out task request
        task_dict = task.get_task_by_uuid(task_uuid)

    if not task_dict:
        response_pipeline_logger.warning("Task lookup did not yield any data")
        return

    # filter down to task_request
    task_request_dict = task_dict.get("task_request", {})

    task_name = task_request_dict.get("task", {}).get("task_name", {})

    # response_pipeline_logger.critical(task_request_dict)

    # based off task name, do neo4j actions
    match task_name:
        case "discover neighbors":
            """
            Takes discovered neighbors, and plots them into Neo4j

            """
            neighbor_list = task_response_dict.get("result", {}).get("data", [])

            for neighbor in neighbor_list:
                neighbor_ip = neighbor.get("ip")
                neighbor_mac = neighbor.get("mac")
                # hostname is returned now.
                neighbor_host = neighbor.get("hostname")

                # create host
                new_host_node = Neo4jHostNodeService.create_or_get_node(
                    hostname=neighbor_host,
                )

                # create nic
                new_nic_node = Neo4jNicNodeService.create_or_get_node(
                    mac_address=neighbor_mac
                )

                # create network - shit, need cidr, not just mac ip or hostname.
                # *could* assume that a host is apart of a network if the IP space matches, however
                # there's a chance for false positives.
                # new_network_node = Neo4jNetworkNodeService.create_or_get_node(
                #     mac_address=neighbor_mac
                # )

                # link nic to host
                Neo4jNicNodeService.connect_nic_to_host(
                    hostname=neighbor_host,
                    mac_address=neighbor_mac,
                    ip_address=neighbor_ip,
                )

        case "memstore upload":
            # memstore tracking
            # get implant node, create file node,
            # link them
            # include file hash

            file_name = (
                task_request_dict.get("task", {}).get("args", {}).get("file_name", "")
            )

            file_contents = (
                task_request_dict.get("task", {})
                .get("args", {})
                .get("file_contents", "")  # store as bytes in db
            )

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
                response_pipeline_logger.error(f"Error saving file_preview: {e}")

            try:
                # add 0x for preivew/user knows it's hex
                file_node.file_size_kb = len(decoded_bytes) / 1000  # convert to kb
            except Exception as e:
                response_pipeline_logger.error(f"Error saving file_size_kb: {e}")

            file_node.save()

        # memstore clear and delete
        case "memstore clear":
            # remove all file from host

            # get all files connected to implant
            connected_file_nodes = (
                Neo4jMemstoreFileNodeService.get_all_files_nodes_for_implant(
                    implant_uuid=implant_uuid
                )
            )
            for node in connected_file_nodes:
                node.delete()

        case "memstore delete":
            # remove all file from host

            file_name = (
                task_request_dict.get("task", {}).get("args", {}).get("file_name", "")
            )

            # the one file connected to the implant
            # note - this might create it if it doesn't exist for some reason, just for it to be deleted.
            file_node = Neo4jMemstoreFileNodeService.create_or_get_node(
                file_name=file_name
            )
            # and delete it
            if file_node:
                file_node.delete()

        # file upload/download
        case "file upload":
            # get file name, contents, path
            # add node

            file_path = (
                task_request_dict.get("task", {}).get("args", {}).get("file_path", "")
            )

            file_contents = (
                task_request_dict.get("task", {})
                .get("args", {})
                .get("file_contents", "")  # store as bytes in db
            )

            host_node = Neo4jImplantNodeService.get_host_implant_is_connected_to(
                implant_uuid
            )

            if not host_node:
                response_pipeline_logger.error(
                    "Could not find host that implant is connected to"
                )
                return

            hostname = host_node.hostname

            decoded_bytes = base64.b64decode(file_contents)
            hash = hashlib.md5(decoded_bytes).hexdigest()

            Neo4jFileNodeService.connect_file_to_host(
                file_path=file_path, hostname=hostname, file_hash_md5=hash
            )

            # addtl metadata
            file_node = Neo4jFileNodeService.create_or_get_node(file_path)

            try:
                # add 0x for preivew/user knows it's hex
                file_node.file_preview = "0x" + decoded_bytes.hex()[:20]
            except Exception as e:
                response_pipeline_logger.error(f"Error saving file_preview: {e}")

            try:
                # add 0x for preivew/user knows it's hex
                file_node.file_size_kb = len(decoded_bytes) / 1000  # convert to kb
            except Exception as e:
                response_pipeline_logger.error(f"Error saving file_size_kb: {e}")

            file_node.save()

        # I don't have a file delete, damn.
        case "file delete":
            file_name = (
                task_request_dict.get("task", {}).get("args", {}).get("file_name", "")
            )

            # the one file connected to the implant
            # note - this might create it if it doesn't exist for some reason, just for it to be deleted.
            file_node = Neo4jFileNodeService.create_or_get_node(file_name=file_name)
            # and delete it
            if file_node:
                file_node.delete()

        # could do a file clear, that attempts to nuke all files, which would use the get_all_files_nodes_for_host
