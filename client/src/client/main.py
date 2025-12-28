from nicegui import app, ui
import logging
import client.src.client.log
import sys
import asyncio

# notes, just import your page here and it'll do the import python magic to add it to the web interface
# also, use full paths due to nicegui being picky about relative paths
import client.src.client.pages.operations
import client.src.client.pages.search
import client.src.client.pages.scripts


server_log = logging.getLogger("server")

# TLDR: windows has different asyncio functionality, need to switch to it if we're on win
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ui.run(native=True, dark=True)
ui.run(native=False, dark=True, show=False)
