import logging
import platform

from nicegui import app, ui

import client.src.client.log
import client.src.client.pages.listeners

# notes, just import your page here and it'll do the import python magic to add it to the web interface
# also, use full paths due to nicegui being picky about relative paths
import client.src.client.pages.operations
import client.src.client.pages.payloads
import client.src.client.pages.scripts
import client.src.client.pages.search

server_log = logging.getLogger("server")


# ui.run(native=True, dark=True)
ui.run(
    native=False, dark=True, show=False, reload=False
)  # reload=platform.system() != "Windows")
# reload false to disable reload, which breaks async on windows
# https://github.com/zauberzeug/nicegui/issues/486
