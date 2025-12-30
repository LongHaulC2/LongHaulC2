# listener supervisor
import multiprocessing
import logging
from .http.http import run as http_run
from ..schemas.listeners import ListenerCreate

listeners = {}  # pid -> Process object. internal, the start/stop keep track of pid's.
# ex: {1234-1234-1234-1234:process_object}

# problem, listeners get added to db, witout a "state". Need to udpate state to be like disabled at sutodwn, etc. otherwise
# the api things the listeners are still up & existing.

server_logger = logging.getLogger("server")


def start_listener(
    listener_data: ListenerCreate,
):  # maybe add the dataclass for pulling out data, would work well with decision tree for listeners to start
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

        case _:
            server_logger.warning(
                f"Invalid listener type: {listener_data.listener_type}"
            )


def get_pid_from_uuid(listener_uuid):
    p = listeners.get(listener_uuid)
    return p.pid


def stop_listener(listener_uuid: str):
    server_logger.info(f"Stopping listener {listener_uuid}")
    pid = get_pid_from_uuid(listener_uuid=listener_uuid)
    proc = listeners.pop(pid, None)
    if proc:
        proc.terminate()
        proc.join()  # this may block


def stop_all():
    server_logger.info(f"Stopping all listeners")
    # for pid in list(listeners):
    #     stop_listener(pid)
    for listener_uuid in listeners:
        stop_listener(listener_uuid=listener_uuid)
