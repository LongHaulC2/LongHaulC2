import threading
import time
import logging

from ..db.mysql_connector import get_mysql_session
from .mysql_functions import ListenerService, ImplantService, MySQLImplantTaskService
from .redis_functions import RedisImplantTaskService

server_logger = logging.getLogger("server")


def start_task_batch_job():
    server_logger.info("Starting listener watchdog")
    t = threading.Thread(target=_task_batch_job, daemon=True)
    t.start()


def _task_batch_job():
    print("uwu task batch job")

    """
        Potential improvement to not lose data:

        peek response → write peeked responses → commit → pop X responses off of queue
    
        Currently, it pops, then writes, which if that fails, loses the response

    """

    while True:

        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            all_implants = implant_service.get_all()

            for implant in all_implants:
                print(implant.id)

                rits = RedisImplantTaskService(implant.id)
                response_queue_length = rits.respone_queue_length()

                # batch write to db
                responses_to_insert = []
                for _ in range(response_queue_length):
                    task_response_dict = rits.dequeue_response_dict()
                    responses_to_insert.append(task_response_dict)

                if responses_to_insert:
                    msits = MySQLImplantTaskService(
                        implant_id=implant.id, session=session
                    )
                    msits.bulk_update_responses(responses=responses_to_insert)

        time.sleep(5)

    # get all current implant ID's from DB
    # loop over all inbox keys in redis.
    # pop all response keys
    # store in sql

    # sleep 1 sec?
