import os
from pathlib import Path

import structlog
from dotenv import load_dotenv
from nicegui import app, ui

# note: # noqa: F401 ignores these in RUFF. TLDR, these need to get
# imported to render the page/register it
import client.log  # noqa: F401
import client.modules.health_check  # noqa: F401
import client.pages.admin_users  # noqa: F401
import client.pages.audit  # noqa: F401
import client.pages.comms  # noqa: F401
import client.pages.docs  # noqa: F401
import client.pages.error  # noqa: F401
import client.pages.filestore  # noqa: F401
import client.pages.graph  # noqa: F401
import client.pages.listeners  # noqa: F401
import client.pages.login  # noqa: F401
import client.pages.logout  # noqa: F401
import client.pages.node.file  # noqa: F401
import client.pages.node.host  # noqa: F401
import client.pages.node.implant  # noqa: F401
import client.pages.node.listener  # noqa: F401
import client.pages.node.network  # noqa: F401
import client.pages.node.nic  # noqa: F401
import client.pages.node.payload  # noqa: F401

# notes, just import your page here and it'll do the import python magic to add it to the web interface
# also, use full paths due to nicegui being picky about relative paths
import client.pages.operations  # noqa: F401
import client.pages.payloads  # noqa: F401
import client.pages.profile  # noqa: F401
import client.pages.profile_preview  # noqa: F401
import client.pages.status  # noqa: F401
import client.pages.user_settings  # noqa: F401

server_log = structlog.getLogger("server")

# load in CSS for our theme
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
app.add_static_files(
    local_directory=str(STATIC_DIR),
    url_path="/static",
)

# load in .env items
load_dotenv()
STORAGE_SECRET = os.getenv("NICEGUI_STORAGE_SECRET")

ui.add_head_html('<link rel="stylesheet" type="text/css" href="/static/theme.css">', shared=True)
# favicon was busted when calling via ui.run, so we inject it here
ui.add_head_html('<link rel="icon" type="image/x-icon" href="/static/favicon.ico">', shared=True)
# a tweak for native to allow dl's
# https://github.com/zauberzeug/nicegui/issues/3402
app.native.settings["ALLOW_DOWNLOADS"] = True


UI_CERT_FILE = os.getenv("UI_CERT_FILE")
UI_CERT_KEY = os.getenv("UI_CERT_KEY")


def main():
    ssl_kwargs = {}
    if UI_CERT_FILE and UI_CERT_KEY and Path(UI_CERT_FILE).exists() and Path(UI_CERT_KEY).exists():
        ssl_kwargs["ssl_certfile"] = UI_CERT_FILE
        ssl_kwargs["ssl_keyfile"] = UI_CERT_KEY

    ui.run(
        native=False,
        dark=True,
        show=False,
        reload=True,
        port=8083,
        storage_secret=STORAGE_SECRET,
        title="LongHaulC2",
        reconnect_timeout=30,  # how long browser waits for server to re-connect, tldr, longer better for
        # heavy UI style tasks.
        loop="uvloop",  # use UVloop for uvicorn, apparently its a lot faster
        **ssl_kwargs,
    )
    # reload=platform.system() != "Windows")
    # reload false to disable reload, which breaks async on windows
    # https://github.com/zauberzeug/nicegui/issues/486


if __name__ in {"__main__", "__mp_main__"}:
    main()
