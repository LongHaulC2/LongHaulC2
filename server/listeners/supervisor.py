# listener supervisor
import multiprocessing
import threading

import structlog

from ..db.neo4j_functions import Neo4jListenerNodeService
from ..instance import active_processes
from ..schemas.listeners import ListenerCreate
from ..utils.checks import check_type
from .raw.raw import run as raw_run


class InvalidListenerType(Exception):
    pass


listeners_lock = threading.Lock()
listeners = {}  # UUID -> Process object. internal, the start/stop keep track of pid's.
# ex: {1234-1234-1234-1234:process_object}

# problem, listeners get added to db, without a "state". Need to update state to be like disabled at shutdown,
# etc. otherwise the api thinks the listeners are still up & existing.

server_logger = structlog.getLogger("server")


def restart_active_listeners():
    """
    Restarts active listeners after a shutdown, etc.

    """
    # grab listeners with active flag, and restart
    ls = Neo4jListenerNodeService()
    all_listeners = ls.get_all()
    for listener in all_listeners:
        if listener.listener_active:
            # create our dataclass with listener data, as that's what the start endpoint wants
            # note, listener is a sql object, so need to convert to dict then pass for a proper unpacking
            listener_dict = listener.to_dict()
            listener_data = ListenerCreate(**listener_dict)
            start_listener(listener_data)


def start_listener(
    listener_data: ListenerCreate,
):
    check_type(listener_data, ListenerCreate, "listener_data")

    try:
        server_logger.info("Starting listener", listener_uuid=listener_data.listener_uuid)

        # could be less code, but for explicity/expandability it's not.
        # Also this allows for per listener kwargs if needed.
        match listener_data.listener_type:
            case "pivot_smb":
                # smb is a pivot listener, so we don't need to actually start one.
                # it's used for a placeholder/interal for templating.
                server_logger.info("SMB listener - not actually starting, but registered.")

                # server_logger.warning("Invalid listener type", listener_type=listener_data.listener_type)
                # throw custom error if invalid listener type
                # raise InvalidListenerType

            case "raw":
                p = multiprocessing.Process(
                    target=raw_run,
                    kwargs={
                        "listener_uuid": listener_data.listener_uuid,
                        "listener_host": listener_data.listener_host,
                        "listener_port": listener_data.listener_port,
                        "listener_profile_contents": listener_data.listener_profile_contents,
                    },
                    daemon=True,
                )
                active_processes[listener_data.listener_name] = p
                p.start()
                with listeners_lock:
                    listeners[listener_data.listener_uuid] = p
                server_logger.info(
                    "Listener started",
                    listener_uuid=listener_data.listener_uuid,
                    pid=p.pid,
                    type=listener_data.listener_type,
                )

            case _:
                server_logger.warning("Invalid listener type", listener_type=listener_data.listener_type)
                # throw custom error if invalid listener type
                raise InvalidListenerType

    except Exception as e:
        server_logger.error(e)
        raise e


def get_pid_from_uuid(listener_uuid: str):
    check_type(listener_uuid, str, "listener_uuid")

    # THREAD-SAFE READ

    with listeners_lock:
        p = listeners.get(listener_uuid)
    if not p:
        raise KeyError(f"Listener {listener_uuid} not found")
    return p.pid


def stop_listener(listener_uuid: str):
    check_type(listener_uuid, str, "listener_uuid")

    try:
        server_logger.info("Stopping listener", listener_uuid=listener_uuid)
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
        server_logger.info("Stopping all listeners")
        # list creates a snapshot of the current listeners to operate on
        with listeners_lock:
            snapshot = list(listeners.keys())
        for listener_uuid in snapshot:
            stop_listener(listener_uuid)

    except Exception as e:
        server_logger.error(e)
        raise e
