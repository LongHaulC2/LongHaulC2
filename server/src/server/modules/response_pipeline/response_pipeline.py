"""
response_pipeline:

Arguably the cornerstone of this whole project, the response pipeline is responsible for handling responses *from*
redis, to where they need to go.

This includes:
 - Writing to MYSQL for retrieval by the GUI
 - Passing responses to neo4j logic to update said relationships there.

"""

# note for performance metrics, the most "efficent" way may be dumping to redis, or using direct metric libs like
# prometheus, isntead of doing a custom metrics system

import concurrent.futures
import threading
import time

import msgpack
import structlog

from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLImplantTaskService
from ...db.neo4j_functions import (
    Neo4jImplantNodeService,
)
from ...db.redis_functions import RedisImplantTaskService
from ...instance import active_threads
from .neo4j_correlator import correlate_task_results

response_pipeline_logger = structlog.getLogger("response_pipeline")
server_logger = structlog.getLogger("server")


def start_task_batch_job():
    # log this explicity with server main logger
    server_logger.info("Starting task watchdog")
    t = threading.Thread(target=_task_batch_job, daemon=True)
    active_threads["response_pipeline"] = t
    t.start()


def _task_batch_job():
    response_pipeline_logger.info("Starting task batch job")

    # get our context outside of the thread so we don't re-setup the executor var a bazilliion times
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        while True:
            try:
                # one sessino a loop to prevent stale session issues.

                unpacked_responses_list = []

                # get all implants at time of loop (could cache this in the future, or only go based on redis keys,
                # but for now it's easier to get all of them to check)
                implants = Neo4jImplantNodeService.get_all()  # ImplantService(session).get_all()

                future_to_implant = {
                    executor.submit(_get_tasks_from_redis_and_write_to_mysql, implant): implant for implant in implants
                }

                for future in concurrent.futures.as_completed(future_to_implant):
                    try:
                        responses = future.result()
                        if responses:
                            unpacked_responses_list.extend(responses)
                    except Exception as e:
                        response_pipeline_logger.error("Thread error", error=e)

                # Neo4j placeholder
                if unpacked_responses_list:
                    for response in unpacked_responses_list:
                        correlate_task_results(response)
                    # _neo4j_placeholder(response_list=unpacked_responses_list)

                time.sleep(1)

            except Exception as e:
                response_pipeline_logger.critical("Global error in task batch job", error=e)
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
            response_pipeline_logger.error("Failed to unpack msgpack", implant_uuid=implant_uuid, error=e)

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

            # nuke old redis entries, ltrim trims to start,end, so if we had 4 entries that we processed above, 0,1,2,3
            #  would be popped, and the value in 4 would be moved to 0.

            # This makes it okay to have new entries come in, and they don't get deleted as we only trim the number
            # we processed.
            rits.redis.ltrim(rits.inbox_key, len(raw_responses), -1)

            if len(responses_to_insert) > 0:
                response_pipeline_logger.debug(
                    "Synced tasks", number_of_tasks=len(responses_to_insert), implant_uuid=implant_uuid
                )

            # finally, return the responses that were inserted, to the parent for addtl handling
            return responses_to_insert

        except Exception as e:
            session.rollback()
            response_pipeline_logger.error("DB Write failed", implant_uuid=implant_uuid, error=e)
            return []
