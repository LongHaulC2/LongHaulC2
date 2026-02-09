import logging
import threading
import time

from ...db.mysql_connector import get_mysql_session
from ..mysql_functions import ImplantService, MySQLImplantTaskService
from ..redis_functions import RedisImplantTaskService

server_logger = logging.getLogger("server")


def start_task_batch_job():
    server_logger.info("Starting listener watchdog")
    t = threading.Thread(target=_task_batch_job, daemon=True)
    t.start()


def _task_batch_job():
    server_logger.info("Starting task batch job")

    """
        Potential improvement to not lose data:

        peek response → write peeked responses → commit → pop X responses off of queue
    
        Currently, it pops, then writes, which if that fails, loses the response

    """

    while True:
        with get_mysql_session() as session:
            implant_service = ImplantService(session)

            # showing up wit none
            all_implants = implant_service.get_all()

            for implant in all_implants:

                rits = RedisImplantTaskService(implant.implant_uuid)
                response_queue_length = rits.response_queue_length()

                # super noisy
                # server_logger.debug(
                #     f"Implant {implant.implant_uuid} has {response_queue_length} tasks to insert"
                # )
                # only log when there's actual data
                if response_queue_length > 1:
                    server_logger.debug(
                        f"Implant {implant.implant_uuid} has {response_queue_length} tasks to insert"
                    )

                # batch write to db
                responses_to_insert = []
                for _ in range(0, response_queue_length):
                    task_response_dict = rits.dequeue_response_dict()
                    responses_to_insert.append(task_response_dict)

                if responses_to_insert:
                    msits = MySQLImplantTaskService(
                        implant_uuid=implant.implant_uuid, session=session
                    )
                    msits.bulk_update_responses(responses=responses_to_insert)

        # Commit the changes for all implants processed in this batch
        try:
            session.commit()
        except Exception as e:
            server_logger.error(f"Failed to commit batch: {e}")
            session.rollback()

        time.sleep(1)

    # get all current implant ID's from DB
    # loop over all inbox keys in redis.
    # pop all response keys
    # store in sql

    # sleep 1 sec?
