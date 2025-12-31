# listener supervisor
import multiprocessing
import logging
from .http.http import run as http_run
from ..schemas.listeners import ListenerCreate


class InvalidListenerType(Exception):
    pass


listeners = {}  # pid -> Process object. internal, the start/stop keep track of pid's.
# ex: {1234-1234-1234-1234:process_object}

# problem, listeners get added to db, witout a "state". Need to udpate state to be like disabled at sutodwn, etc. otherwise
# the api things the listeners are still up & existing.

server_logger = logging.getLogger("server")


def start_listener(
    listener_data: ListenerCreate,
):
    try:
        server_logger.info(f"Starting listener {listener_data.listener_uuid}")

        # could be less code, but for explicity/expandability it's not.
        # Also this allows for per listener kwargs if needed.
        match listener_data.listener_type:
            case "http":
                p = multiprocessing.Process(
                    target=http_run,
                    kwargs={
                        "listener_uuid": listener_data.listener_uuid,
                    },
                    daemon=True,  # shuts down listeners at program exit.
                )
                p.start()
                listeners[listener_data.listener_uuid] = p
                print(p.pid)

            case _:
                server_logger.warning(
                    f"Invalid listener type: {listener_data.listener_type}"
                )
                # throw custom error if invalid listener type
                raise InvalidListenerType

    except Exception as e:
        server_logger.error(e)
        raise e


def get_pid_from_uuid(listener_uuid):
    try:
        p = listeners.get(listener_uuid)
        return p.pid

    except Exception as e:
        server_logger.error(e)
        raise e


def stop_listener(listener_uuid: str):
    try:
        server_logger.info(f"Stopping listener {listener_uuid}")
        # pid = get_pid_from_uuid(listener_uuid=listener_uuid)
        proc = listeners.pop(listener_uuid, None)
        if proc:
            proc.terminate()
            proc.join()  # this may block

    except Exception as e:
        server_logger.error(e)
        raise e


def stop_all():
    try:
        server_logger.info(f"Stopping all listeners")
        for listener_uuid in listeners:
            stop_listener(listener_uuid=listener_uuid)
    except Exception as e:
        server_logger.error(e)
        raise e
