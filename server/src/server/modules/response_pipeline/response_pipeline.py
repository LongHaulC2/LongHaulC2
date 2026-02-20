"""
response_pipeline:

Arguably the cornerstone of this whole project, the response pipeline is responsible for handling responses *from* redis, to where they need to go.

This includes:
 - Writing to MYSQL for retrieval by the GUI
 - Passing responses to neo4j logic to update said relationships there.

"""

# note for performance metrics, the most "efficent" way may be dumping to redis, or using direct metric libs like prometheus, isntead of doing a custom metrics system

import concurrent.futures
import logging
import threading
import time

import msgpack

from ...db.mysql_connector import get_mysql_session
from ...db.neo4j_models import Neo4jHostNode, Neo4jImplantNode
from ...modules.neo4j_functions import Neo4jHostNodeService
from ..mysql_functions import ImplantService, MySQLImplantTaskService
from ..redis_functions import RedisImplantTaskService

server_logger = logging.getLogger("server")


def start_task_batch_job():
    server_logger.info("Starting task watchdog")
    t = threading.Thread(target=_task_batch_job, daemon=True)
    t.start()


def _task_batch_job():
    server_logger.info("Starting task batch job")

    # get our context outside of the thread so we don't re-setup the executor var a bazilliion times
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        while True:
            try:
                # one sessino a loop to prevent stale session issues.

                unpacked_responses_list = []

                # get all implants at time of loop (could cache this in the future, or only go based on redis keys, but for now it's easier to get all of them to check)
                with get_mysql_session() as session:
                    implants = ImplantService(session).get_all()

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
                            server_logger.error(f"Thread error: {e}")

                # Neo4j placeholder
                if unpacked_responses_list:
                    for response in unpacked_responses_list:
                        process_single_response_for_neo4j(response)
                    # _neo4j_placeholder(response_list=unpacked_responses_list)

                time.sleep(1)

            except Exception as e:
                server_logger.critical(f"Global error in task batch job: {e}")
                time.sleep(1)


def _get_tasks_from_redis_and_write_to_mysql(implant) -> list:
    """
    Atomically moves tasks from Redis to MySQL for a single implant.

    note, using raw redis queries. Put them in redis_functions.py later.
    """

    rits = RedisImplantTaskService(implant.implant_uuid)

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
            server_logger.error(
                f"Failed to unpack msgpack for {implant.implant_uuid}: {e}"
            )

    if not responses_to_insert:
        # Queue had data, but it was all corrupt. Clear it so we don't loop forever.
        rits.redis.ltrim(rits.inbox_key, len(raw_responses), -1)
        return []

    #  Write to MySQL
    with get_mysql_session() as session:
        try:
            msits = MySQLImplantTaskService(
                implant_uuid=implant.implant_uuid,
                session=session,
            )
            # write all responses at once to not pound the db
            msits.bulk_update_responses(responses=responses_to_insert)
            session.commit()

            # nuke old redis entries, ltrim trims to start,end, so if we had 4 entries that we processed above, 0,1,2,3 would be popped, and the value in 4 would be moved to 0.
            # This makes it okay to have new entries come in, and they don't get deleted as we only trim the number we processed.
            rits.redis.ltrim(rits.inbox_key, len(raw_responses), -1)

            if len(responses_to_insert) > 0:
                server_logger.debug(
                    f"Synced {len(responses_to_insert)} tasks for {implant.implant_uuid}"
                )

            # finally, return the responses that were inserted, to the parent for addtl handling
            return responses_to_insert

        except Exception as e:
            session.rollback()
            server_logger.error(f"DB Write failed for {implant.implant_uuid}: {e}")
            return []


# def _neo4j_placeholder(response_list: list):
#     server_logger.debug(f"neo4j placeholder: list len: {len(response_list)}")

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
    # server_logger.critical("IT IS WORKING")
    task_uuid = task_response_dict.get("task_uuid", "")
    implant_uuid = task_response_dict.get("implant_uuid")

    if not task_uuid:
        server_logger.warning("Task response did not have a task_uuid")
        return

    if not implant_uuid:
        server_logger.warning("Task response did not have a implant_uuid")
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
        server_logger.warning("Task lookup did not yield any data")
        return

    # filter down to task_request
    task_request_dict = task_dict.get("task_request", {})

    task_name = task_request_dict.get("task", {}).get("task_name", {})

    # server_logger.critical(task_request_dict)

    # based off task name, do neo4j actions
    match task_name:
        # create implant if the task was to register
        # fuck so register is not one we do I think, as it never "has" a response from the client iirc. So
        # the node should probably be created when the implant checks in, otherwise it'll wait for a response
        case "ls":
            new_implant = Neo4jImplantNode(implant_uuid=implant_uuid)
            new_implant.save()
        case "register":
            new_implant = Neo4jImplantNode(implant_uuid=implant_uuid)
            new_implant.save()

        case "discover neighbors":
            # for ref, task struct: {'implant_uuid': '019c7c3a-ebe5-7a7e-a229-eb1ee8084921', 'result': {'data': {'type': 'text', 'value': '10.0.0.1\n10.0.0.10\n10.0.0.25\n10.0.0.30\n'}, 'message': {'type': 'text', 'value': 'Success'}, 'windows_error_code': {'type': 'int', 'value': 0}}, 'task_uuid': '019c7c3c-db72-7be1-9f14-46c9bdc8076f'}
            data = task_response_dict.get("result", {}).get("data", "").get("value", "")
            addresses = data.split()  # get addr from respnose
            # parse neighbor discovery and add node

            for address in addresses:
                # clean address
                address = address.strip()
                new_host = Neo4jHostNodeService(address=address)
                new_host.register_host()

    # okay works, however gui does not know what these nodes are, it's not defined tehre yet.
    # also, add auto compelte to the gui, with list of comamnds, should be preetty easy
