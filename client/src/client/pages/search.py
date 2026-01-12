import asyncio
import logging
from typing import Optional

import httpx
from nicegui import events, ui

from client.src.client.pages.menu import setup_menu

# from client.src.client.pages.menu import setup_menu
from client.src.client.style import (
    BUTTON_COLOR,
    HIGHLIGHT_COLOR,
    ICON_COLOR,
    NAVBAR_COLOR,
    TEXT_COLOR,
)
from client.src.client.utils.url import generate_url

from ..utils.checks import check_type

server_log = logging.getLogger("server")

server_log.info("Loading /search page")


@ui.page("/search")
async def search():
    # HEY- readme: This is a hack to get the page full screen (and make h-full work). It should also allow for things like headers to fit without adjusting it manually
    # see the link below.
    # https://github.com/zauberzeug/nicegui/discussions/4049
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    ui.context.client.content.classes("h-full")

    setup_menu("Event Search")
    with ui.element().classes("w-full h-full"):
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
        .classes(f"w-1/2 mt-24 mx-auto")
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


async def implants_list_layout(data: list[dict]):
    """
    Implant table view. Similar to the operations view, with reduced functionality.
    """

    check_type(data, list, "data")

    table = (
        ui.table(
            columns=[],  # filled later
            rows=[],
            row_key="uuid",
            # selection="multiple",  # no selection, no use here currently.
            # on_select=lambda e: ui.notify(f"selected: {e.selection}"),
            pagination=100,
        )
        .classes(f"w-full no-shadow {TEXT_COLOR}")
        .props("dense virtual-scroll")
        # virtual scroll only renders items on screen. Helpful when a large amount of items exist in the table.")
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

    # https://nicegui.io/documentation/table#table_cells_with_html
    # adding HTML rendering in.
    # Slightly diff than example, but still renders correctly. Also, only adding on AFTER initilization, otherwise
    # there's an error about the notes row not existing (which is expected with dynamic row generation)
    # ALSO: <div style="max-height: 20px; max-width: 300px; overflow: hidden;">  keeps the row a max size to not blow up the screen
    # this is slightly bigger  than the operations tab, for easier viewing
    table.add_slot(
        "body-cell-notes",
        """
            <q-td :props="props">
                <div style="max-height: 20px; max-width: 300px; overflow: hidden; word-wrap: break-word; white-space: normal;"> 
                    <!-- <span v-html="props.row.notes"></span> -->
                    <!-- v-if only applies if the row/data actually exists, which saves some JS work -->
                    <span v-if="props.row.notes" v-html="props.row.notes"></span>
            </q-td>
        """,
    )

    # finally, Update table rows
    table.rows = data
    table.update()


async def tasks_list_layout(data): ...
