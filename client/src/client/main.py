import logging
import platform

from nicegui import app, ui

import client.src.client.log
import client.src.client.pages.implant
import client.src.client.pages.listeners
import client.src.client.pages.login

# notes, just import your page here and it'll do the import python magic to add it to the web interface
# also, use full paths due to nicegui being picky about relative paths
import client.src.client.pages.operations
import client.src.client.pages.payloads
import client.src.client.pages.scripts
import client.src.client.pages.search

server_log = logging.getLogger("server")

# attempt at css
print("HARDCODED STATIC DIRECTORY FOR CSS LOADING!")
app.add_static_files(
    local_directory="/home/ubuntu-dev/LongHaulC2/client/src/client/static",
    url_path="/static",
)
ui.add_head_html(
    '<link rel="stylesheet" type="text/css" href="/static/theme.css">', shared=True
)


# ui.run(native=True, dark=True)
ui.run(
    native=False, dark=True, show=False, reload=False
)  # reload=platform.system() != "Windows")
# reload false to disable reload, which breaks async on windows
# https://github.com/zauberzeug/nicegui/issues/486
