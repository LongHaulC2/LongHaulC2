import httpx
from nicegui import ui
import logging
from client.src.client.utils.url import generate_url
from client.src.client.modules.task_definitions import task_tree, ResultType
from client.src.client.modules.api_calls import queue_task
from client.src.client.pages.menu import setup_menu
from nicegui.events import KeyEventArguments

# from client.src.client.pages.menu import setup_menu
from client.src.client.style import (
    BUTTON_COLOR,
    TEXT_COLOR,
    HIGHLIGHT_COLOR,
    NAVBAR_COLOR,
    ICON_COLOR,
)

server_log = logging.getLogger("server")

server_log.info("Loading /operations page")


"""
Notes:


The terminal is very "open", by having a few  module specific variables that allow for access to terminal functions. See:

tabs = None
panels = None
open_tabs = {}


These allow for `terminal_add_tab`, `terminal_close_tab`, and tracking of current open terminal tabs.

"""


@ui.page("/")
@ui.page("/operations")
async def operations():
    # HEY- readme: This is a hack to get the page full screen (and make h-full work). It should also allow for things like headers to fit without adjusting it manually
    # see the link below.
    # https://github.com/zauberzeug/nicegui/discussions/4049
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    ui.context.client.content.classes("h-full")

    setup_menu("Operations")

    with ui.splitter(horizontal=True, value=50).classes("w-full h-full") as splitter:
        with splitter.before:
            await implant_view()
        with splitter.after:
            # await implant_view()
            await terminal_view()


async def get_implant_data() -> dict:
    # get implants
    async with httpx.AsyncClient() as client:
        url = generate_url("/api/v1/implants/")
        response = await client.get(url)
        data = response.json().get("data")
        return data


async def delete_implant(id=int) -> None:
    # get implants
    async with httpx.AsyncClient() as client:
        url = generate_url(f"/api/v1/implants/{id}")
        response = await client.delete(url)


async def implant_view():
    """
    Implant table view

    Creates the table for on screen, initially blank.

    Then, every 1 seconds, gets the new API data, and udpates the table based on it.
    """

    # Keep track of previous implant IDs
    previous_ids = set()
    table_initialized = False  # track if table columns are already built. Solves the bug of saying that every implant in the table is a new connection

    # Setup header
    with ui.row().classes("w-full items-center justify-between"):

        # LEFT: title / context
        ui.label("Implants").classes(f"text-h6 dense {TEXT_COLOR}")

        # RIGHT: action buttons
        with ui.row().classes("items-center q-gutter-xs"):

            with ui.button(
                icon="terminal", on_click=lambda: action_open_terminal()
            ).props("dense flat round").classes(f"[&_.q-icon]:{ICON_COLOR}"):
                ui.tooltip("Open shell")

            # note, can do this 2 ways:
            # 1. loop over all  clients and send a req per client (gets really slow on a large number of clients)
            # OR
            # 2. Send one request to a dedicated godshell endpoint, and then let it distribute to all (this is more efficent, but takes more setup)
            with ui.button(
                icon="present_to_all", on_click=lambda: action_open_terminal()
            ).props("dense flat round disabled color=amber"):
                ui.tooltip("God Shell")

            with ui.button(
                icon="notes",
            ).props(f"dense flat round disabled").classes(
                f"[&_.q-icon]:{ICON_COLOR}"
            ):  # change JUST the icon color
                ui.tooltip("Open notes")

            with ui.button(
                icon="refresh",
                on_click=lambda: refresh(),
            ).props("dense flat round").classes(
                f"[&_.q-icon]:{ICON_COLOR}"
            ):  # change JUST the icon color:
                ui.tooltip("Refresh")

            with ui.button(
                icon="delete",
                on_click=lambda: action_delete_rows(),
            ).props("dense flat round color=negative"):
                ui.tooltip("Delete selected implants")

    ui.separator()

    table = (
        ui.table(
            columns=[],  # filled later
            rows=[],
            row_key="id",
            selection="multiple",
            # on_select=lambda e: ui.notify(f"selected: {e.selection}"),
            pagination=100,
        )
        .classes(f"w-full no-shadow {TEXT_COLOR}")
        .props("dense")
    )

    # add button to table
    # https://nicegui.io/documentation/table#table_with_buttons
    # table.add_slot(
    #     "body-cell-interact",
    #     """
    #     <q-td :props="props">
    #         <q-btn
    #             label="Interact"
    #             flat
    #             @click="() => $parent.$emit('interact', props.row)"
    #             class="text-caption" //caption matches the rest of the text in the table
    #         />
    #     </q-td>
    #     """,
    # )
    # table.on("Interact", lambda e: ui.notify(f'Implant {e.args["id"]} cllicked!'))

    async def refresh():
        nonlocal previous_ids  # use the variable above that's in the implant_view scope, to track id's between calls
        nonlocal table_initialized  # track if table columns are already built. Solves the bug of saying that every implant in the table is a new connection

        data = await get_implant_data()
        if not data:
            return

        # Detect new implants
        current_ids = {row["id"] for row in data if "id" in row}

        # bypassing, causes client crash on high amount of notifications
        # if table_initialized:
        # new_ids = current_ids - previous_ids
        # for new_id in new_ids:
        #     ui.notify(
        #         f"New implant with ID {new_id} has connected", color="positive"
        #     )

        previous_ids = current_ids

        # Build columns only once
        if not table_initialized:
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

            # # manually add column for interact
            # table.columns.append(
            #     {
            #         "name": "interact",
            #         "label": "Interact",
            #         "field": "interact",
            #         "align": "center",
            #     }
            # )

            table_initialized = True  # mark table as initialized, meaning the first time setup is done & basic data is loaded in.

        # Update table rows
        table.rows = data
        table.update()

    async def action_delete_rows():
        ids = [row["id"] for row in table.selected]

        if not ids:
            ui.notify("No rows selected", color="warning")
            return

        for implant_id in ids:
            # do request
            await delete_implant(id=implant_id)

            # bug, rows are still "checked" after deleting

    async def action_open_terminal():
        ids = [row["id"] for row in table.selected]

        if not ids:
            ui.notify("No implants selected", color="warning")
            return

        for implant_id in ids:
            await terminal_add_tab(implant_id, implant_id)

    ui.timer(1, refresh)


# -------------------------------
# Terminal
# -------------------------------
# global tabs for being able to access tab functions & vars without doing some weirder stuff
tabs = None
panels = None
open_tabs = {}


# redfined to be accessible anywhere, maek the vars gllobal to this module
async def terminal_view():
    global tabs, panels

    # init tabs and panel view (basically just a container that exists)
    # width/height full set here
    tabs = ui.tabs().props("dense indicator-color=grey")
    panels = (
        ui.tab_panels(tabs).classes("w-full h-full")
        # transition is set to 0, this disables the nauseating "panel slide"
        .props("dense transition-duration=0")
    )


# Global function to add a tab from anywhere
async def terminal_add_tab(tab_name, implant_id):
    global tabs, panels, open_tabs

    # already open → switch
    if implant_id in open_tabs:
        panels.set_value(open_tabs.get("implant_id"))
        return

    # create tab
    with tabs:
        # create tab with implant_id metadata  for identifying it later
        with ui.tab(tab_name, label="").classes("p-0 rounded-none") as tab:
            tab.meta = {"implant_id": implant_id}

            with ui.row().classes("items-center gap-0"):
                # implant id (could make into ip as well)
                ui.label(implant_id).classes("px-3 py-1 text-sm border-l")
                # close button
                ui.button("✕", on_click=lambda e=tab_name: terminal_close_tab(e)).props(
                    "flat dense"
                ).classes("w-6 h-full px-0 text-xs rounded-none  border-r")

    # create panel
    with panels:
        with ui.tab_panel(tab_name):
            await terminal(implant_id)

    # register specific tab object in tab dict
    open_tabs[implant_id] = {"tab_object": tab}

    # and switch to it
    panels.set_value(tab_name)


async def terminal_close_tab(implant_id):
    global tabs, open_tabs

    tab_object = open_tabs[implant_id]["tab_object"]
    # remove the tab from the tab object
    tabs.remove(tab_object)
    # remove from dict
    open_tabs.pop(implant_id)


async def terminal(implant_id):
    terminal_prepend = f"{implant_id} > "
    ui_log = ui.log().classes("w-full h-full")

    with ui.row().classes("w-full items-center"):
        # This splits 90% of the line into the UI input, and 10% into the send button
        ui_user_input = (
            ui.input()
            .classes("flex-grow")
            .props("dense autofocus")
            .style(f"--q-primary: {HIGHLIGHT_COLOR}")
            # use the .on to  trigger the send action if a user presses enter
            .on("keydown.enter", lambda e: handle_command())
        )

        # Button logic: On click, push the value of the user input to the log
        ui.button(
            "Send", color=BUTTON_COLOR, on_click=lambda: handle_command()
        ).classes(f"w-[10%]").props("dense")

    # Setup message to indicate the terminal is connected
    async def setup_terminal():
        await push_text_to_terminal(f"Connected to {implant_id}")

    async def handle_command():
        # get user input from ui input
        user_input = ui_user_input.value

        # push to terminal for visibilty
        await push_text_to_terminal(user_input)
        await clear_input()

        # error check for no command input
        if user_input == None or user_input == "":
            await push_error_to_terminal("No input provided")
            return

        # split input and args
        parts = user_input.split()
        command = parts[0]
        args = parts[1:]  # list of everything after the cmd
        args = " ".join(
            args
        )  # Keeping args joined for now. This lets the task_definitions handle them.

        result_type, result_data = task_tree(command=command, args=args)

        # on task, queue task
        if result_type == ResultType.TASK:
            await queue_task(implant_id=implant_id, task=result_data.to_task())

        # on data, push to screen
        elif result_type == ResultType.TEXT:
            await push_text_to_terminal(result_data)

        elif result_type == ResultType.LIST:
            await push_list_to_terminal(result_data)

        elif result_type == ResultType.ERROR:
            await push_error_to_terminal(result_data)

    async def push_text_to_terminal(data):
        ui_log.push(f"{terminal_prepend}{data}")

    async def push_list_to_terminal(list_data):
        for line in list_data:
            ui_log.push(line, classes="text-blue")

    async def push_error_to_terminal(data):
        ui_log.push(f"[!] {data}", classes="text-orange")

    async def clear_input():
        ui_user_input.value = ""

    await setup_terminal()
