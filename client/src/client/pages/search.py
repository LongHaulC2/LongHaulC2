import httpx
from nicegui import ui, events
import logging
from client.src.client.pages.menu import setup_menu
from client.src.client.utils.url import generate_url
from typing import Optional
import asyncio


# from client.src.client.pages.menu import setup_menu
from client.src.client.style import (
    BUTTON_COLOR,
    TEXT_COLOR,
    HIGHLIGHT_COLOR,
    NAVBAR_COLOR,
    ICON_COLOR,
)

server_log = logging.getLogger("server")

server_log.info("Loading /search page")


@ui.page("/search")
async def search():
    setup_menu()
    # ui.label("search")
    await search_to_type()


async def search_to_type():
    #!/usr/bin/env python3

    api = httpx.AsyncClient()
    running_query: Optional[asyncio.Task] = None

    async def search(e: events.ValueChangeEventArguments) -> None:
        """Search for data as you type"""
        nonlocal running_query

        if running_query:
            running_query.cancel()  # cancel the previous query; happens when you type fast

        # define endpoints
        # note, add search endpoints for better/more efficent searching, that only returns necessary data
        if selector_button.text == "Implant Search":
            url = generate_url("/api/v1/implants/search")
            # POST /api/v1/search/implants
            display_func = implants_list_layout
        elif selector_button.text == "Task Search":
            # doesn't exist yet, gets ALL history of ALL the implants
            url = generate_url("/api/v1/implants/history/search")
            # POST /api/v1/search/implants/history
            display_func = tasks_list_layout

        search_field.classes("mt-2", remove="mt-24")  # move the search field up
        results.clear()

        request_body = {"search_term": search_field.value}

        # store the http coroutine in a task so we can cancel it later if needed
        running_query = asyncio.create_task(
            api.post(
                # put api call here
                # f"https://www.thecocktaildb.com/api/json/v1/1/search.php?s={e.value}"
                url,
                json=request_body,
            )
        )
        response = await running_query
        if response.text == "":
            return
        with results:  # enter the context of the results row
            # make this more robust
            # have a row that is clickable that opens in a "client" window.
            query_data = response.json().get("data")
            await display_func(data=query_data)

        running_query = None

    # create a search field which is initially focused and leaves space at the top
    search_field = (
        ui.input(on_change=search)
        .props("autofocus outlined flat")
        .classes(f"w-1/2 self-center mt-24")
        .style(f"--q-primary: {HIGHLIGHT_COLOR};")
    )

    # add dropdown to search field
    with search_field.add_slot("prepend"):
        # shadow won't go away D:
        selector_button = (
            ui.dropdown_button(
                "Implant Search",
                auto_close=True,
            )
            .props("flat dense")
            .classes("no-shadow")
        )

        # updates the text to be what the user selected
        def select_mode(label: str):
            selector_button.text = label

        with selector_button:
            ui.item("Implant Search", on_click=lambda: select_mode("Implant Search"))
            ui.item("Task Search", on_click=lambda: select_mode("Task Search"))
    results = ui.row()


# async def implants_list_layout(data):
#     """
#     implants_list_layout. Creates a layout for implants list
#     :param data: JSON data to display in the results list
#     """
#     # using flex here as that is the only layout that wouldn't squish values together
#     with ui.list().props("bordered separator").classes("w-full justify-center"):
#         # ui.item_label("Results").props("header").classes("text-bold ")

#         # ui.separator()
#         for entry in data:
#             implant_id = entry.get("id")
#             internal_ip = entry.get("internal_ip")
#             external_ip = entry.get("external_ip")
#             listener = entry.get("listener")
#             process = entry.get("process")
#             sleep = entry.get("sleep")
#             system_hostname = entry.get("system_hostname")
#             user = entry.get("user")

#             with ui.item(on_click=lambda: ui.notify(f"Selected: {implant_id}")):
#                 # This is the container for each item
#                 with ui.row().classes(
#                     "items-center justify-between space-x-4"
#                 ):  # Use flex row
#                     with ui.column().classes("flex-1"):
#                         ui.item_label(implant_id).classes("text-bold")

#                     with ui.column().classes("flex-1"):
#                         ui.item_label(internal_ip)

#                     with ui.column().classes("flex-1"):
#                         ui.item_label(external_ip)

#                     with ui.column().classes("flex-1"):
#                         ui.item_label(listener)

#                     with ui.column().classes("flex-1"):
#                         ui.item_label(process)

#                     with ui.column().classes("flex-1"):
#                         ui.item_label(sleep)

#                     with ui.column().classes("flex-1"):
#                         ui.item_label(system_hostname)

#                     with ui.column().classes("flex-1"):
#                         ui.item_label(user)

#                     with ui.column().props("side").classes("ml-4"):
#                         ui.icon("open_in_new")


async def implants_list_layout(data: list[dict]):
    """
    Implant table view. Similar to the operations view, with reduced functionality.
    """

    table = (
        ui.table(
            columns=[],  # filled later
            rows=[],
            row_key="id",
            # selection="multiple",  # no selection, no use here currently.
            # on_select=lambda e: ui.notify(f"selected: {e.selection}"),
            pagination=100,
        )
        .classes(f"w-full no-shadow {TEXT_COLOR}")
        .props("dense")
    )

    # if no search results, DO NOT continue with dynamic generation of table
    # This *will* show an empty table. Move above the table def to not do that.
    if data == None or data == []:
        return

    # if not table.columns:
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

    # finally, Update table rows
    table.rows = data
    table.update()


async def tasks_list_layout(data): ...
