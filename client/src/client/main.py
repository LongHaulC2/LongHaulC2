from nicegui import app, ui
import logging
import client.src.client.log
import platform

# notes, just import your page here and it'll do the import python magic to add it to the web interface
# also, use full paths due to nicegui being picky about relative paths
import client.src.client.pages.operations
import client.src.client.pages.search
import client.src.client.pages.scripts


server_log = logging.getLogger("server")


# ui.run(native=True, dark=True)
ui.run(
    native=False, dark=True, show=False, reload=platform.system() != "Windows"
)  # reload false to disable reload, which breaks async on windows
