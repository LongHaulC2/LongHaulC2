import os
from pathlib import Path

import structlog
from dotenv import load_dotenv
from nicegui import app, ui

# note: # noqa: F401 ignores these in RUFF. TLDR, these need to get
# imported to render the page/register it
import client.src.client.log  # noqa: F401
import client.src.client.modules.health_check  # noqa: F401
import client.src.client.pages.docs  # noqa: F401
import client.src.client.pages.error  # noqa: F401
import client.src.client.pages.filestore  # noqa: F401
import client.src.client.pages.graph  # noqa: F401
import client.src.client.pages.listeners  # noqa: F401
import client.src.client.pages.login  # noqa: F401
import client.src.client.pages.logout  # noqa: F401
import client.src.client.pages.node.file  # noqa: F401
import client.src.client.pages.node.host  # noqa: F401
import client.src.client.pages.node.implant  # noqa: F401
import client.src.client.pages.node.listener  # noqa: F401
import client.src.client.pages.node.network  # noqa: F401
import client.src.client.pages.node.nic  # noqa: F401
import client.src.client.pages.node.payload  # noqa: F401

# notes, just import your page here and it'll do the import python magic to add it to the web interface
# also, use full paths due to nicegui being picky about relative paths
import client.src.client.pages.operations  # noqa: F401
import client.src.client.pages.payloads  # noqa: F401
import client.src.client.pages.scripts  # noqa: F401
import client.src.client.pages.status  # noqa: F401
import client.src.client.pages.user_settings  # noqa: F401

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


def main():
    # ui.run(native=True, dark=True)
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
    )
    # reload=platform.system() != "Windows")
    # reload false to disable reload, which breaks async on windows
    # https://github.com/zauberzeug/nicegui/issues/486


if __name__ in {"__main__", "__mp_main__"}:
    main()
