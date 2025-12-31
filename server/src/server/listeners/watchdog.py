from .supervisor import listeners, listeners_lock

import threading
import time
import logging

from ..db.mysql_connector import get_mysql_session
from ..modules.mysql_functions import ListenerService

server_logger = logging.getLogger("server")


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
                server_logger.warning(f"Listener {listener_uuid} invalid process state")
                with listeners_lock:
                    listeners.pop(listener_uuid, None)
                continue

            if not proc.is_alive():
                print(f"{listener_uuid}: offline")
                server_logger.warning(
                    f"Listener {listener_uuid} went offline (pid={proc.pid})"
                )

                # cleanup dead listener
                proc.join(timeout=0)

                with listeners_lock:
                    listeners.pop(listener_uuid, None)

                # mark as inactive in the DB
                with get_mysql_session() as session:
                    listener_service = ListenerService(session)
                    listener_service.set_active(listener_uuid, active=False)
