import threading
import time

import structlog

from ..db.mysql_connector import get_mysql_session
from ..modules.mysql_functions import ListenerService
from .supervisor import listeners, listeners_lock

server_logger = structlog.getLogger("server")


def start_watchdog():
    server_logger.info("Starting listener watchdog")
    t = threading.Thread(target=_watchdog, daemon=True)
    t.start()


def _watchdog():
    while True:
        time.sleep(1)

        # snapshot listeners safely
        with listeners_lock:
            snapshot = list(listeners.items())

        for listener_uuid, proc in snapshot:
            # Process was never started or already cleaned up
            if proc is None or proc.pid is None:
                server_logger.warning("Listener invalid process state", listener_uuid=listener_uuid)
                with listeners_lock:
                    listeners.pop(listener_uuid, None)
                continue

            if not proc.is_alive():
                server_logger.warning("Listener went offline", listener_uuid=listener_uuid, pid=proc.pid)

                # cleanup dead listener
                proc.join(timeout=0)

                with listeners_lock:
                    listeners.pop(listener_uuid, None)

                # mark as inactive in the DB
                with get_mysql_session() as session:
                    listener_service = ListenerService(session)
                    listener_service.set_active(listener_uuid, active=False)
                    session.commit()
