import logging
import threading
import time

import msgpack

from ...db.mysql_connector import get_mysql_session
from ..mysql_functions import ImplantService, MySQLImplantTaskService
from ..redis_functions import RedisImplantTaskService

server_logger = logging.getLogger("server")


def start_task_batch_job():
    server_logger.info("Starting task watchdog")
    t = threading.Thread(target=_task_batch_job, daemon=True)
    t.start()


# bug - if this crashes, no messages come in as there's nothing parsing anymore.
def _task_batch_job():
    server_logger.info("Starting task batch job")

    while True:
        try:
            # one sessino a loop to prevent stale session issues.
            with get_mysql_session() as session:
                implant_service = ImplantService(session)
                all_implants = implant_service.get_all()

                for implant in all_implants:
                    try:
                        # hit one implant at a time.
                        # If one fails, it doesn't block others
                        _process_single_implant(implant, session)
                    except Exception as e:
                        server_logger.error(
                            f"Error processing implant {implant.implant_uuid}: {e}"
                        )

            time.sleep(1)

        except Exception as e:
            server_logger.critical(f"Global error in task batch job: {e}")
            time.sleep(1)


def _process_single_implant(implant, session):
    """
    Atomically moves tasks from Redis to MySQL for a single implant.

    note, using raw redis queries. Put them in redis_functions.py later.
    """
    rits = RedisImplantTaskService(implant.implant_uuid)

    queue_length = rits.response_queue_length()
    # save the hassle of addtl code if there's no responses.
    if queue_length == 0:
        return

    # peek data, don't pop as we could lose it then.
    raw_responses = rits.redis.lrange(rits.inbox_key, 0, -1)

    if not raw_responses:
        return

    # Convert from messagepack to dict
    responses_to_insert = []
    for packed in raw_responses:
        try:
            # Assuming you fixed the raw=False issue or use the custom decoder
            data = msgpack.unpackb(packed, raw=False)
            responses_to_insert.append(data)
        except Exception as e:
            server_logger.error(
                f"Failed to unpack msgpack for {implant.implant_uuid}: {e}"
            )

    if not responses_to_insert:
        # Queue had data, but it was all corrupt. Clear it so we don't loop forever.
        rits.redis.ltrim(rits.inbox_key, len(raw_responses), -1)
        return

    #  Write to MySQL
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

    except Exception as e:
        session.rollback()
        server_logger.error(f"DB Write failed for {implant.implant_uuid}: {e}")
