# listener supervisor
import multiprocessing

from .http.http import run as http_run

listeners = {}  # pid -> Process object. internal, the start/stop keep track of pid's.


def start_listener(listener_uuid):
    # logic for type input var?
    p = multiprocessing.Process(
        target=http_run,
        kwargs={
            "listener_uuid": listener_uuid,
        },
    )
    p.start()
    listeners[p.pid] = p


def stop_listener(pid):
    proc = listeners.pop(pid, None)
    if proc:
        proc.terminate()
        proc.join()  # this may block


def stop_all():
    for pid in list(listeners):
        stop_listener(pid)
