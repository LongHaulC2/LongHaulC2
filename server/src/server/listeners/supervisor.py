# listener supervisor
import multiprocessing
import logging
from .http.http import run as http_run
from ..schemas.listeners import ListenerCreate
import threading


class InvalidListenerType(Exception):
    pass


listeners_lock = threading.Lock()
listeners = {}  # UUID -> Process object. internal, the start/stop keep track of pid's.
# ex: {1234-1234-1234-1234:process_object}

# problem, listeners get added to db, without a "state". Need to update state to be like disabled at shutdown, etc. otherwise
# the api thinks the listeners are still up & existing.

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
                # THREAD-SAFE ADDITION
                with listeners_lock:
                    listeners[listener_data.listener_uuid] = p
                server_logger.info(
                    f"Listener {listener_data.listener_uuid} started, PID={p.pid}"
                )

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
    # THREAD-SAFE READ
    with listeners_lock:
        p = listeners.get(listener_uuid)
    if not p:
        raise KeyError(f"Listener {listener_uuid} not found")
    return p.pid


def stop_listener(listener_uuid: str):
    try:
        server_logger.info(f"Stopping listener {listener_uuid}")
        # THREAD-SAFE POP
        with listeners_lock:
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
        # list creates a snapshot of the current listeners to operate on
        with listeners_lock:
            snapshot = list(listeners.keys())
        for listener_uuid in snapshot:
            stop_listener(listener_uuid)

    except Exception as e:
        server_logger.error(e)
        raise e
