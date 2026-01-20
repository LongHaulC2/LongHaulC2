import logging

import httpx
from nicegui import ui
from nicegui.events import KeyEventArguments

from client.src.client.modules.api_calls import (
    get_all_implant_data,
    get_implant_data,
    get_implant_task_history,
    get_implant_task_history_since_uuid,
    queue_task,
    update_implant,
)
from client.src.client.modules.task_definitions import ResultType, task_tree
from client.src.client.pages.implants import start_implant_dialogue
from client.src.client.pages.listeners import start_listener_dialogue
from client.src.client.pages.menu import setup_menu
from client.src.client.pages.notes import open_notes_dialog

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

server_log.info("Loading /operations page")


"""
Notes:


The terminal is very "open", by having a few  module specific variables that allow for access to terminal functions. See:

tabs = None
panels = None
open_tabs = {}


These allow for `terminal_add_tab`, `terminal_close_tab`, and tracking of current open terminal tabs.

"""
# global tabs for being able to access tab functions & vars without doing some weirder stuff
tabs = None
panels = None
open_tabs = {}


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

    # bug fix - on refresh, clear open tabs in dict, otherwise open tabs has stale tab data
    global open_tabs
    open_tabs = {}

    with ui.splitter(horizontal=True, value=50).classes("w-full h-full") as splitter:
        with splitter.before:
            await implant_view()
        with splitter.after:
            # await implant_view()
            await terminal_view()


async def delete_implant(implant_uuid=str) -> None:
    check_type(implant_uuid, str, "implant_uuid")

    # get implants
    async with httpx.AsyncClient() as client:
        url = generate_url(f"/api/v1/implants/{implant_uuid}")
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

            with ui.button(icon="add", on_click=lambda: start_implant_dialogue()).props(
                "dense flat round"
            ).classes(f"[&_.q-icon]:{ICON_COLOR}"):
                ui.tooltip("Create a new implant payload")

            with ui.button(
                icon="headphone", on_click=lambda: start_listener_dialogue()
            ).props("dense flat round").classes(f"[&_.q-icon]:{ICON_COLOR}"):
                ui.tooltip("Start a new listener")

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

            with ui.button(icon="notes", on_click=lambda: handle_notes()).props(
                f"dense flat round"
            ).classes(
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
            row_key="implant_uuid",
            selection="multiple",
            # on_select=lambda e: ui.notify(f"selected: {e.selection}"),
            pagination=100,
        )
        .classes(f"w-full no-shadow {TEXT_COLOR}")
        .props("dense virtual-scroll")
        # virtual scroll only renders items on screen. Helpful when a large amount of items exist in the table.
    )

    async def refresh():
        nonlocal previous_ids  # use the variable above that's in the implant_view scope, to track implant_uuid's between calls
        nonlocal table_initialized  # track if table columns are already built. Solves the bug of saying that every implant in the table is a new connection

        data = await get_all_implant_data()
        data = data.get("data")
        if not data:
            server_log.debug("No data from implant")
            return

        # bypassing, causes client crash on high amount of notifications
        # Detect new implants
        # current_ids = {row["implant_uuid"] for row in data if "implant_uuid" in row}
        # if table_initialized:
        # new_ids = current_ids - previous_ids
        # for new_id in new_ids:
        #     ui.notify(
        #         f"New implant with ID {new_id} has connected", color="positive"
        #     )
        # revious_ids = current_ids

        # Build columns only once
        if not table_initialized:
            # using tuple as rows are NOT re-created/edit
            # previous iterations used a list derived from the inital row
            keys = tuple(data[0].keys())
            table.columns = [
                {
                    "name": key,
                    "label": key.replace("_", " ").title(),
                    "field": key,
                    "sortable": True,
                    "align": "left",
                }
                for key in keys
            ]
            # https://nicegui.io/documentation/table#table_cells_with_html
            # adding HTML rendering in.
            # Slightly diff than example, but still renders correctly. Also, only adding on AFTER initilization, otherwise
            # there's an error about the notes row not existing (which is expected with dynamic row generation)
            # ALSO: <div style="max-height: 20px; max-width: 300px; overflow: hidden;">  keeps the row a max size to not blow up the screen
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

            table_initialized = True  # mark table as initialized, meaning the first time setup is done & basic data is loaded in.

        # Update table rows
        table.rows = data
        table.update()

    async def action_delete_rows():
        ids = [row["implant_uuid"] for row in table.selected]

        if not ids:
            ui.notify("No rows selected", color="warning")
            return

        for implant_uuid in ids:
            # do request
            await delete_implant(implant_uuid=implant_uuid)

            # bug, rows are still "checked" after deleting

    async def action_open_terminal():
        ids = [row["implant_uuid"] for row in table.selected]

        if not ids:
            ui.notify("No implants selected", color="warning")
            return

        for implant_uuid in ids:
            await terminal_add_tab(implant_uuid, implant_uuid)

    async def handle_notes():
        # get all selected
        ids = [row["implant_uuid"] for row in table.selected]
        # if selected = 1, pull up notes from that agent and populate editor with them

        if len(ids) == 1:
            implant_uuid = ids[0]
            # lookup server value of notes, NOT what's currently in the table. Server is source of truth
            implant_data = await get_implant_data(implant_uuid=implant_uuid)
            implant_notes = implant_data.get("data", {}).get("notes")

            # get notes from dialog
            notes = await open_notes_dialog(
                implant_uuid=f"ID: {implant_uuid}", populate_editor_with=implant_notes
            )
            # ui.notify(notes)
            data = {"notes": notes}
            # post to update implant
            await update_implant(implant_uuid=implant_uuid, data=data)

        elif len(ids) > 1:
            notes = await open_notes_dialog(
                implant_uuid=f"Editing {len(ids)} implants notes"
            )
            # ui.notify(notes)
            # post to update all the implants
            data = {"notes": notes}

            for implant_uuid in ids:
                await update_implant(implant_uuid=implant_uuid, data=data)

        else:
            ui.notify("Please select an implant to edit its notes")
        #

    ui.timer(1, refresh)


# -------------------------------
# Terminal
# -------------------------------


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
async def terminal_add_tab(tab_name: str, implant_uuid: str):
    global tabs, panels, open_tabs

    check_type(tab_name, str, "tab_name")
    check_type(implant_uuid, str, "implant_uuid")

    try:
        # already open → switch
        if implant_uuid in open_tabs:
            server_log.info(f"Tab {implant_uuid} already open")
            panels.set_value(open_tabs.get("implant_uuid"))
            return

        # create tab
        with tabs:
            # create tab with implant_uuid metadata  for identifying it later
            with ui.tab(tab_name, label="").classes("p-0 rounded-none") as tab:
                tab.meta = {"implant_uuid": implant_uuid}

                with ui.row().classes("items-center gap-0"):
                    # implant implant_uuid (could make into ip as well)
                    ui.label(implant_uuid).classes("px-3 py-1 text-sm border-l")
                    # close button
                    ui.button(
                        "✕",
                        on_click=lambda e=tab_name: terminal_close_tab(
                            implant_uuid
                        ),  # (e)
                    ).props("flat dense").classes(
                        "w-6 h-full px-0 text-xs rounded-none  border-r"
                    )

        # create panel
        # with panels:
        #     with ui.tab_panel(tab_name):
        #         await terminal(implant_uuid)
        with panels:
            with ui.tab_panel(tab_name) as panel:
                await terminal(implant_uuid)

        # register specific tab object in tab dict
        open_tabs[implant_uuid] = {
            "tab_object": tab,
            "panel_object": panel,
        }

        # and switch to it
        panels.set_value(tab_name)
    except Exception as e:
        server_log.error(e)


async def terminal_close_tab(implant_uuid: str):
    global tabs, panels, open_tabs

    check_type(implant_uuid, str, "implant_uuid")

    try:
        tab_data = open_tabs.pop(implant_uuid)

        tab = tab_data["tab_object"]
        panel = tab_data["panel_object"]

        tabs.remove(tab)
        panels.remove(panel)

        # Optional: switch to another tab if any exist
        if open_tabs:
            next_uuid = next(iter(open_tabs))
            panels.set_value(next_uuid)
        else:
            panels.set_value(None)

    except Exception as e:
        server_log.error(e)


async def terminal(implant_uuid: str):
    check_type(implant_uuid, str, "implant_uuid")

    terminal_prepend = f"{implant_uuid} > "

    """
    Note: If scroll bar at bottom, this auto updates to new content.  If not, it does not jump to neweset content
    Seems to be the best of both worlds.

    Does NOT set to bottom on terminal open - need a way to set that still
    """
    ui_log = ui.log().classes("w-full h-full")

    last_uuid = None

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
        task_history = await get_implant_task_history(implant_uuid)
        if not task_history:
            server_log.info("No task history to display")
            return
        tasks = task_history.get("data") or []
        if not isinstance(tasks, list):
            server_log.warning("Task history data is not a list")
            return

        await add_tasks_to_terminal(tasks)

        # finally, set last uuid
        # set this ONCE - only when tab is init'd, so all tasks *past* this get updates from here.
        nonlocal last_uuid
        last_item = tasks[-1]
        last_uuid = last_item.get("task_uuid")

        msg_for_user = (
            "──────────────────────────────────────────────\n"
            " Heads Up\n"
            "──────────────────────────────────────────────\n"
            " • All prior communications are displayed above\n"
            " • New commands and responses will appear below\n"
            "\n"
            " If anything looks missing:\n"
            "   - Re-open the terminal\n"
            "   - Run the `history` command\n"
            "   - Or view the implant page for full context\n"
            " • FYI - The terminal will auto scroll when the scroll bar is set to the lowest position\n"
            " • Have fun, Don't break anything :)\n"
            "──────────────────────────────────────────────"
        )
        await push_output_to_terminal(msg_for_user)

        # https://github.com/zauberzeug/nicegui/discussions/5268
        # scrolls ui.log to bottom. Can change "last" to "first" to scroll to top
        ui.run_javascript(
            f"""
            const logElement = document.querySelector('.q-scrollarea__content');
            if (logElement && logElement.lastElementChild) {{
                logElement.lastElementChild.scrollIntoView();
            }}
            """
        )

        # scroll  to bottom
        # await push_text_to_terminal(f"Connected to {implant_uuid}")

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

        result_type, result_data = await task_tree(
            command=command, args=args, implant_uuid=implant_uuid
        )

        # on task, queue task
        if result_type == ResultType.TASK:
            await queue_task(implant_uuid=implant_uuid, task=result_data)

        # on data, push to screen
        elif result_type == ResultType.TEXT:
            await push_text_to_terminal(result_data)

        elif result_type == ResultType.LIST:
            await push_list_to_terminal(result_data)

        elif result_type == ResultType.ERROR:
            await push_error_to_terminal(result_data)

    async def push_text_to_terminal(data):
        ui_log.push(f"[placeholder timestamp]{terminal_prepend}{data}")

    async def push_list_to_terminal(list_data):
        for line in list_data:
            ui_log.push(line, classes="text-blue")

    async def push_error_to_terminal(data):
        ui_log.push(f"[!] {data}", classes="text-orange")

    async def push_output_to_terminal(data):
        ui_log.push(f"{data}")

    async def clear_input():
        ui_user_input.value = ""

    async def add_tasks_to_terminal(task_list: list[dict]):
        """Adds tasks to the terminal

        Args:
            task_list: A list of tasks
        """
        nonlocal last_uuid

        # pull data out
        for task in task_list:
            if not isinstance(task, dict):
                continue

            # Always coerce None → {}
            task_request = task.get("task_request") or {}
            task_response = task.get("task_response") or {}

            # skip empty tasks
            # if not task_request and not task_response:
            #     continue

            # push request to term
            if task_request:
                # get task, and the name
                taskname = task_request.get("task", {}).get("taskname", "<no-taskname>")
                # get the args
                args = task_response.get("task", {}).get("args", {})

                # Then format the command to look like the input
                formatted_task_request = taskname
                if args:
                    formatted_task_request += " " + " ".join(
                        f"{k}={v}" for k, v in args.items()
                    )
                await push_text_to_terminal(formatted_task_request)

            # either print task or print no result
            if task_response:
                await push_output_to_terminal(task_response.get("data", ""))
                await push_output_to_terminal(" ")  # newline push

            else:
                await push_error_to_terminal("No task result")
                await push_output_to_terminal(" ")  # newline push

        # update last uuid to not re-hit it
        # warning - this will hide old tasks results if they update late
        # this is probably fine, there's going to be a history command
        last_item = task_list[-1]
        last_uuid = last_item.get("task_uuid")

    # async def update_terminal():
    #     nonlocal last_uuid

    #     # last uuid is set by setup_terminal
    #     # call out to endponit to get all data since this
    #     task_history = await get_implant_task_history_since_uuid(
    #         implant_uuid, since_task_uuid=last_uuid
    #     )
    #     if not task_history:
    #         # could get noisy running every second
    #         server_log.info("No task history to display")
    #         return

    #     tasks = task_history.get("data") or []
    #     if not isinstance(tasks, list):
    #         server_log.warning("Task history data is not a list")
    #         return
    #     if not tasks:
    #         # no tasks
    #         return

    #     # await add_tasks_to_terminal(tasks)
    #     # trying responses only
    #     for task in tasks:
    #         if not isinstance(task, dict):
    #             continue

    #         # Always coerce None → {}
    #         task_request = task.get("task_request") or {}
    #         task_response = task.get("task_response") or {}

    #         # *only* print out a new task result if there is one.
    #         if task_response:
    #             await push_output_to_terminal(task_response.get("data", ""))
    #             await push_output_to_terminal(" ")  # newline push

    #     # update last uuid to not re-hit it
    #     # warning - this will hide old tasks results if they update late
    #     # this is probably fine, there's going to be a history command

    #     # buuuuug this is updating last_uuid before showing on screen
    #     last_item = tasks[-1]
    #     last_uuid = last_item.get("task_uuid")

    #     # if len(tasks) >= 2:
    #     #     last_uuid = tasks[-2].get("task_uuid")
    #     # else:
    #     #     last_uuid = None

    # fixes skipped responses, plus late arriving responses.
    async def update_terminal():
        nonlocal last_uuid

        task_history = await get_implant_task_history_since_uuid(
            implant_uuid, since_task_uuid=last_uuid
        )
        if not task_history:
            return

        tasks = task_history.get("data") or []
        if not tasks:
            return

        new_last_uuid = last_uuid  # cursor candidate

        for task in tasks:
            if not isinstance(task, dict):
                continue

            task_response = task.get("task_response") or {}

            if task_response:
                await push_output_to_terminal(task_response.get("data", ""))
                await push_output_to_terminal(" ")
                new_last_uuid = task.get("task_uuid")

        # advance cursor ONLY to last displayed task
        last_uuid = new_last_uuid

    await setup_terminal()
    timer = ui.timer(1, update_terminal)
