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

    # works, but screen gets cleared/current state wiped out
    # ui.timer(5.0, lambda: implant_view.refresh())


async def get_implant_data() -> dict:
    # get implants
    async with httpx.AsyncClient() as client:
        url = generate_url("/api/v1/implants/")
        response = await client.get(url)
        data = response.json().get("data")
        return data


# old way of doing it, this nukes the table of ALL data, and re-created it. Adds flashing & state loss for the user. Not acceptable.
# @ui.refreshable
# async def implant_view():
#     # setup default widgets
#     a = ui.label("SOME HEADER")  # create the label first
#     data = await get_implant_data()
#     # Update the label after async I/O
#     # a.set_text(str(data))
#     with ui.card().classes("w-full h-full no-shadow"):
#         # derive the keys/column data based on the first entry in the data
#         first_row = data[0]
#         columns = [
#             {
#                 "name": key,
#                 # title turns "ur mom"  into "Ur Mom"
#                 "label": key.replace("_", " ").title(),
#                 "field": key,
#                 "sortable": True,
#                 "align": "left",
#             }
#             for key in first_row.keys()
#         ]

#         # Use 'id' as row_key if available
#         row_key = "id" if "id" in first_row else None

#         ui.table(
#             columns=columns,
#             rows=data,
#             row_key=row_key,
#             selection="multiple",
#             # on_select=lambda x: ui.notify("SELECTED"),
#         ).classes("w-full no-shadow").props("dense")


async def implant_view():
    """
    Implant table view

    Creates the table for on screen, initially blank.

    Then, every 1 seconds, gets the new API data, and udpates the table based on it.
    """

    ui.label("SOME HEADER")

    table = (
        ui.table(
            columns=[],  # filled later
            rows=[],
            row_key="id",
            selection="multiple",
        )
        .classes("w-full no-shadow")
        .props("dense")
    )

    async def refresh():
        data = await get_implant_data()
        if not data:
            return

        # Build columns only once
        if not table.columns:
            first_row = data[0]
            table.columns = [
                {
                    "name": key,
                    "label": key.replace("_", " ").title(),
                    "field": key,
                    "sortable": True,
                    "align": "left",
                }
                for key in first_row.keys()
            ]

        table.rows = data
        table.update()

    ui.timer(1, refresh)
