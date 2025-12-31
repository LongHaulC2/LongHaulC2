from .supervisor import listeners

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

        for listener_uuid, proc in list(listeners.items()):
            # Process was never started or already cleaned up
            if proc is None or proc.pid is None:
                print(f"{listener_uuid}: offline")
                continue

            # if process goes offline
            if not proc.is_alive():
                print(f"{listener_uuid}: offline")
                server_logger.warning(
                    f"Listener {listener_uuid} went offline (pid={proc.pid})"
                )

                # cleanup, commenting out for now, otherwise listener won't be in the list anymore
                # there's more robustness I could do here in the future with processses & restarts.
                # proc.join(timeout=0)
                # listeners.pop(listener_uuid, None)

                # and mark as inactive in the DB.
                with get_mysql_session() as session:
                    listener_service = ListenerService(session)
                    listener_service.set_active(listener_uuid, active=False)
