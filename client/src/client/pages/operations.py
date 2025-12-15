import httpx
from nicegui import ui
import logging
from client.src.client.utils.url import generate_url

server_log = logging.getLogger("server")

server_log.info("Loading /operations page")

@ui.page('/operations')
async def operations():
    await implant_view()


async def implant_view():
    # setup default widgets
    a = ui.label("PLACEHOLDER")  # create the label first

    # get implants

    async with httpx.AsyncClient() as client:
        url = generate_url("/api/v1/implants/")
        response = await client.get(url)
        data = response.json()

    # Update the label after async I/O
    a.set_text(str(data))
    with ui.card().classes("w-full h-full no-shadow"):
        ui.table(rows={}, columns={})