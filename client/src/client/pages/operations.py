import httpx
from nicegui import ui
import logging
from client.src.client.utils.url import generate_url

server_log = logging.getLogger("server")

server_log.info("Loading /operations page")


@ui.page("/operations")
async def operations():
    # HEY- readme: This is a hack to get the page full screen (and make h-full work). It should also allow for things like headers to fit without adjusting it manually
    # see the link below.
    # https://github.com/zauberzeug/nicegui/discussions/4049
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    ui.context.client.content.classes("h-full")

    with ui.splitter(horizontal=True, value=50).classes("w-full h-full") as splitter:
        with splitter.before:
            await implant_view()
        with splitter.after:
            await implant_view()


async def implant_view():
    # setup default widgets
    a = ui.label("SOME HEADER")  # create the label first

    # get implants

    async with httpx.AsyncClient() as client:
        url = generate_url("/api/v1/implants/")
        response = await client.get(url)
        data = response.json().get("data")

    # Update the label after async I/O
    # a.set_text(str(data))
    with ui.card().classes("w-full h-full no-shadow"):
        # derive the keys/column data based on the first entry in the data
        first_row = data[0]
        columns = [
            {
                "name": key,
                # title turns "ur mom"  into "Ur Mom"
                "label": key.replace("_", " ").title(),
                "field": key,
                "sortable": True,
                "align": "left",
            }
            for key in first_row.keys()
        ]

        # Use 'id' as row_key if available
        row_key = "id" if "id" in first_row else None

        ui.table(
            columns=columns,
            rows=data,
            row_key=row_key,
            selection="multiple",
            # on_select=lambda x: ui.notify("SELECTED"),
        ).classes("w-full no-shadow").props("dense")
