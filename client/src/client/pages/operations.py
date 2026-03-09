import httpx
import structlog
from nicegui import app, ui

from client.src.client.modules.api_calls import (
    get_all_implant_data,
    get_implant_data,
    get_implant_task_history,
    get_implant_task_history_since_uuid,
    queue_task,
    update_implant,
)
from client.src.client.modules.task_parser import ResultType, build_cli_parser, get_all_command_names, task_tree
from client.src.client.pages.dialogues import upload_dialog
from client.src.client.pages.footer import build_footer
from client.src.client.pages.formatted_tooltip import formatted_tooltip
from client.src.client.pages.listeners import start_listener_dialogue
from client.src.client.pages.menu import setup_menu
from client.src.client.pages.notes import open_notes_dialog
from client.src.client.pages.payloads import start_payload_dialogue
from client.src.client.utils.url import generate_url

from ..utils.checks import check_type

server_log = structlog.getLogger("server")
server_log.info("Loading /operations page")

# -------------------------------
# GLOBAL STATE
# -------------------------------
tabs = None
panels = None
open_tabs = {}

# for history per implant terminal
command_history = {}
history_index = {}


def clear_state():
    global tabs, panels, open_tabs
    tabs = None
    panels = None
    open_tabs = {}


@ui.page("/")
@ui.page("/operations")
async def operations():
    # Full Screen Layout Setup
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    clear_state()
    setup_menu("Operations")

    # Main Layout (Splitter)
    # Using a container that matches the background
    with ui.element().classes("w-full h-full gap-0"):  # noqa: SIM117
        # Splitter: Left (Implants) vs Right (Terminal)
        with ui.splitter(horizontal=True, value=50, limits=(10, 99)).classes("w-full h-full").props(
            "separator-class=bg-white/10"
        ) as splitter:
            with splitter.before:
                await implant_view()

            with splitter.after:
                await terminal_view()

            with splitter.separator:
                ui.icon("drag_handle").classes("text-emerald-700 w-full")

    await build_footer()


async def delete_implant(implant_uuid=str) -> None:
    check_type(implant_uuid, str, "implant_uuid")
    async with httpx.AsyncClient() as client:
        url = generate_url(f"/api/v1/implants/{implant_uuid}")
        await client.delete(url)


# -------------------------------
# IMPLANT VIEW (LEFT PANEL)
# -------------------------------
async def implant_view():
    previous_ids = set()
    table_initialized = False

    # Glass Panel Container
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel rounded-none border-0 border-r border-white/5"):
        # Header Bar
        with ui.row().classes("w-full items-center justify-between tech-header-bar h-14"):
            # Title
            with ui.row().classes("items-center gap-2"):
                ui.icon("terminal", color="emerald-500").classes("text-xl")
                ui.label("ACTIVE_SESSIONS //").classes("tech-label-header-section")

            # Toolbar
            with ui.row().classes("items-center gap-1"):
                # Payloads
                with (
                    ui.button(on_click=lambda: start_payload_dialogue())
                    .classes("tech-btn-action px-2")
                    .props("dense flat size=sm")
                ):
                    ui.icon("add", size="xs").classes("mr-1")
                    ui.label("PAYLOAD").classes("tech-label-sub")
                    formatted_tooltip("Build New Payload")

                with (
                    ui.button(on_click=lambda: start_listener_dialogue())
                    .classes("tech-btn-action px-2")
                    .props("dense flat size=sm")
                ):
                    ui.icon("add", size="xs").classes("mr-1")
                    ui.label("LISTENER").classes("tech-label-sub")
                    formatted_tooltip("Start a Listener")

                ui.separator().classes("bg-white/10 h-4 w-[1px] mx-1")

                # Terminal (Open)
                with (
                    ui.button(icon="terminal", on_click=lambda: action_open_terminal())
                    .classes("tech-btn-action-2 tech-btn-action-2")
                    .props("dense flat size=sm square")
                ):
                    formatted_tooltip("Open Terminal for Selected")

                # God Shell
                # ui.button(
                #     icon="present_to_all", on_click=lambda: action_open_terminal()
                # ).classes(
                #     "text-orange-400 hover:text-orange-200 transition-colors"
                # ).props(
                #     "dense flat size=sm square disabled"
                # ).tooltip(
                #     "God Shell (Coming Soon)"
                # )

                with (
                    ui.button(
                        # get all selected to upload to
                        icon="present_to_all",
                        on_click=lambda: upload_dialog([row["implant_uuid"] for row in table.selected]),
                    )
                    .classes("text-orange-400 hover:text-orange-200 transition-colors tech-btn-action-2")
                    .props("dense flat size=sm square")
                ):
                    formatted_tooltip("Upload File")

                # Notes
                with (
                    ui.button(icon="notes", on_click=lambda: handle_notes())
                    .classes("tech-btn-action-2 tech-btn-action-2")
                    .props("dense flat size=sm square ")
                ):
                    formatted_tooltip("Edit Notes")

                # Refresh
                with (
                    ui.button(icon="refresh", on_click=lambda: refresh())
                    .classes("tech-btn-action-2 tech-btn-action-2")
                    .props("dense flat size=sm square")
                ):
                    formatted_tooltip("Force Refresh")

                ui.separator().classes("bg-white/10 h-4 w-[1px] mx-1")

                # Delete
                with (
                    ui.button(icon="delete", on_click=lambda: action_delete_rows())
                    .classes("text-red-400 hover:text-red-200 transition-colors tech-btn-action-2")
                    .props("dense flat size=sm square")
                ):
                    formatted_tooltip("Nuke Selected")

        # Table Container
        with ui.column().classes(" w-full flex-grow relative overflow-hidden bg-transparent"):
            table = (
                ui.table(
                    columns=[],
                    rows=[],
                    row_key="implant_uuid",
                    selection="multiple",
                    pagination=100,
                )
                .classes("w-full h-full tech-table-base tech-table-head tech-table-body tech-table-row-hover")
                .props("dense flat virtual-scroll square")
            )

    # --- LOGIC ---
    async def refresh():
        nonlocal previous_ids, table_initialized

        data = await get_all_implant_data()
        data = data.get("data")
        if not data:
            return

        if not table_initialized:
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

            # HTML Notes Slot
            table.add_slot(
                "body-cell-notes",
                r"""
<q-td :props="props">
    <div style="max-height: 20px; max-width: 200px; overflow: hidden;" class="opacity-70 text-xs font-mono">
        <span v-if="props.row.notes" v-html="props.row.notes"></span>
    </div>
</q-td>
            """,
            )

            # Custom Tech Header
            table.add_slot(
                "header",
                r"""
<q-tr :props="props" class="bg-white/5 text-neutral-400 uppercase text-xs tracking-wider border-b border-white/10">
    <q-th auto-width />
    <q-th v-for="col in props.cols" :key="col.name" :props="props">
        {{ col.label }}
    </q-th>
</q-tr>
            """,
            )

            table_initialized = True

        table.rows = data
        table.update()

    async def action_delete_rows():
        ids = [row["implant_uuid"] for row in table.selected]

        # Remove rows locally
        table.rows = [row for row in table.rows if row["implant_uuid"] not in ids]

        # Clear selected, this fixes a "selected but not in table" bug when opening a terminal
        table.selected = []

        table.update()

        # Then delete from backend
        for implant_uuid in ids:
            await delete_implant(implant_uuid=implant_uuid)

        await refresh()

    async def action_open_terminal():
        ids = [row["implant_uuid"] for row in table.selected]
        for implant_uuid in ids:
            # FIX: Pass only the full UUID.
            # The function now handles the slicing for the label internally.
            await terminal_add_tab(implant_uuid)

    async def handle_notes():
        ids = [row["implant_uuid"] for row in table.selected]
        if len(ids) == 1:
            implant_uuid = ids[0]
            implant_data = await get_implant_data(implant_uuid=implant_uuid)
            implant_notes = implant_data.get("data", {}).get("notes")
            notes = await open_notes_dialog(implant_uuid=f"ID: {implant_uuid}", populate_editor_with=implant_notes)
            await update_implant(implant_uuid=implant_uuid, data={"notes": notes})
        elif len(ids) > 1:
            notes = await open_notes_dialog(implant_uuid=f"Editing {len(ids)} implants notes")
            for implant_uuid in ids:
                await update_implant(implant_uuid=implant_uuid, data={"notes": notes})
        else:
            ui.notify("Select an implant to edit notes", type="warning", color="orange-9")

    update_time = app.storage.user.get("auto_refresh_rate", 1)
    ui.timer(update_time, refresh)


# -------------------------------
# TERMINAL VIEW (RIGHT PANEL)
# -------------------------------
async def terminal_view():
    global tabs, panels

    # Glass Panel Container
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel rounded-none border-0"):
        # Header / Tabs
        with ui.row().classes("w-full items-center bg-black/20 border-b border-white/5 px-2 h-10 gap-2"):
            ui.icon("terminal", size="xs", color="emerald-500")
            ui.label("TERMINAL //").classes("tech-label-sub")

            # The Tabs Control
            tabs = ui.tabs().props(
                "dense indicator-color=emerald text-color=grey-5 active-color=emerald-400 narrow-indicator align=left"
            )
            tabs.classes("bg-transparent h-full flex-grow")

            ui.separator().classes("bg-white/10 h-4 w-[1px] mx-1")
            with (
                ui.button(icon="delete_sweep", on_click=terminal_close_all)
                .props("flat dense square size=sm")
                .classes("text-neutral-500 hover:text-red-400 transition-colors tech-btn-action-2")
            ):
                formatted_tooltip("Close All Terminals")

        # The Panel Container
        panels = ui.tab_panels(tabs).classes("w-full h-full bg-neutral-900/40").props("dense transition-duration=0")
    # Inside your terminal_view header or tab label
    # label_checkin = ui.label("..").classes("tech-label-sub")

    # async def update_timer():
    #     # Fetch latest data for this implant
    #     data = await get_implant_data(implant_uuid)
    #     last_seen = data.get('last_seen') # timestamp
    #     sleep = data.get('sleep', 5)      # seconds

    #     # Calc logic (pseudo-code)
    #     # seconds_ago = now - last_seen
    #     # next_in = sleep - seconds_ago

    #     if next_in > 0:
    #         label_checkin.text = f"NEXT: {next_in}s"
    #         label_checkin.classes(remove="text-red-500", add="text-neutral-500")
    #     else:
    #         label_checkin.text = f"LATE: {abs(next_in)}s"
    #         label_checkin.classes(remove="text-neutral-500", add="text-red-500")

    # ui.timer(1, update_timer)


async def terminal_add_tab(implant_uuid: str):
    global tabs, panels, open_tabs
    # Remove tab_name argument, we derive it here
    check_type(implant_uuid, str, "implant_uuid")

    # Define distinct ID vs Label
    tab_id = implant_uuid  # Unique internal ID (Full UUID)
    tab_label = implant_uuid[-8:]  # Visual display name, get last 8 of uuid

    # Check using the full UUID key
    if implant_uuid in open_tabs:
        panels.set_value(tab_id)
        return

    # Create Tab with explicit 'name'
    with tabs:  # noqa: SIM117
        # name=tab_id ensures the tab system tracks it by full UUID
        with ui.tab(name=tab_id, label="").classes("h-full px-3 min-h-0 border-r border-white/5") as tab:
            tab.meta = {"implant_uuid": implant_uuid}
            with ui.row().classes("items-center gap-2"):
                # Display the short label visually
                ui.label(tab_label).classes("tech-label-sub")
                ui.button("✕", on_click=lambda: terminal_close_tab(implant_uuid)).props("flat dense size=xs").classes(
                    "text-neutral-600 hover:text-white px-0"
                )

    # Create Panel with matching 'name'
    with panels, ui.tab_panel(name=tab_id).classes("p-0 w-full h-full") as panel:
        await terminal(implant_uuid)

    open_tabs[implant_uuid] = {"tab_object": tab, "panel_object": panel}
    panels.set_value(tab_id)


async def terminal_close_tab(implant_uuid: str):
    global tabs, panels, open_tabs
    try:
        tab_data = open_tabs.pop(implant_uuid)
        tabs.remove(tab_data["tab_object"])
        panels.remove(tab_data["panel_object"])

        # If we just closed the active tab, or any tab, we need to decide what to focus
        if not open_tabs:
            panels.set_value(None)
        # Optional: Else switch to the last opened tab
        # else:
        #    last_uuid = list(open_tabs.keys())[-1]
        #    panels.set_value(last_uuid)

    except Exception as e:
        server_log.error(f"Error closing tab: {e}")


async def terminal_close_all():
    global open_tabs
    # We must iterate over a list copy of keys because the dictionary
    # changes size as we close tabs.
    for implant_uuid in list(open_tabs.keys()):
        await terminal_close_tab(implant_uuid)


async def terminal(implant_uuid: str):
    terminal_prepend = f"{implant_uuid[:8]} > "
    last_uuid = None

    cli_parser = build_cli_parser(implant_uuid="AUTOCOMPLETE")
    list_of_commands_for_autocomplete = get_all_command_names(cli_parser)

    # Layout: Output gets all space, Input gets fixed bottom
    with ui.column().classes("w-full h-full gap-0"):
        # LOG OUTPUT (Scrollable)
        # Using flex-grow to take up all available space
        ui_log = ui.log().classes(
            "w-full flex-grow p-2 font-mono text-xs text-emerald-500/90 bg-transparent overflow-auto"
        )

        # INPUT BAR (Fixed Bottom)
        with ui.row().classes("w-full bg-black/40 border-t border-white/10 p-2 gap-2 items-center"):
            ui.label(terminal_prepend).classes("tech-label-sub")

            ui_user_input = (
                ui.input(autocomplete=list_of_commands_for_autocomplete)
                .classes("flex-grow tech-input")
                .props("dense borderless dark input-class=text-emerald-400 input-style=font-family:monospace")
                .on("keydown.enter", lambda: handle_command())
                .on("keydown.up", lambda: navigate_history("up"))  # <--- Add this
                .on("keydown.down", lambda: navigate_history("down"))
            )

            ui.button("SEND", on_click=lambda: handle_command()).classes("tech-btn-action px-3").props(
                "dense flat size=sm"
            )

    # --- LOGIC ---
    async def push_text_to_terminal(data):
        ui_log.push(f"{terminal_prepend}{data}")

    async def push_output_to_terminal(data):
        ui_log.push(f"{data}")

    async def push_error_to_terminal(data):
        ui_log.push(f"[!] {data}")

    async def handle_command():
        user_input = ui_user_input.value
        # this checks if user input == "", if so, just give the user a newline
        # strip is so we account for everything, such as " ", "  ", and so on
        if not user_input.strip():
            await push_text_to_terminal(data="")
            # set the terminal value back to nothing so the spaces or whatever doesn't stay in it
            ui_user_input.value = ""
            return

        # Save to history
        command_history[implant_uuid].append(user_input)
        history_index[implant_uuid] = -1  # Reset index

        # push user input to terminal so they can "see" the command they just ran
        await push_text_to_terminal(user_input)
        # reset contents of cli bar to nothing
        ui_user_input.value = ""

        # We know parts has at least one item because of the .strip() check above that
        # checks for nothing in the cli bar
        # parts = user_input.split()
        # command = parts[0]
        # args = " ".join(parts[1:])

        result_type, result_data = await task_tree(user_input=user_input, implant_uuid=implant_uuid)

        if result_type == ResultType.TASK:
            await queue_task(implant_uuid=implant_uuid, task=result_data)
        elif result_type == ResultType.TEXT:
            await push_text_to_terminal(result_data)

        elif result_type == ResultType.LIST:
            for line in result_data:
                ui_log.push(line)
        elif result_type == ResultType.CLEAR:
            ui_log.clear()
        elif result_type == ResultType.ERROR:
            await push_error_to_terminal(result_data)

        # last but not least, update autofill
        list_of_commands_for_autocomplete.append(user_input)

    async def add_tasks_to_terminal(task_list: list[dict]):
        nonlocal last_uuid
        for task in task_list:
            if not isinstance(task, dict):
                continue

            task_request = task.get("task_request") or {}
            task_response = task.get("task_response") or {}

            if task_request:
                task_name = task_request.get("task", {}).get("task_name", "?")
                args = task_response.get("task", {}).get("args", {})
                fmt_req = task_name + (" " + " ".join(f"{k}={v}" for k, v in args.items()) if args else "")
                await push_text_to_terminal(fmt_req)

            if task_response:
                await push_output_to_terminal(task_response.get("data", ""))
            else:
                pass  # Awaiting...

        last_item = task_list[-1]
        last_uuid = last_item.get("task_uuid")

    async def update_terminal():
        nonlocal last_uuid
        task_history = await get_implant_task_history_since_uuid(implant_uuid, since_task_uuid=last_uuid)
        if not task_history:
            return

        tasks = task_history.get("data") or []
        if not tasks:
            return

        new_last_uuid = last_uuid
        for task in tasks:
            if not isinstance(task, dict):
                continue
            # print(task)
            task_response = task.get("task_response") or {}
            if task_response:
                for key, value in task_response.items():
                    # output = f"{key}:\n{'-'*10}\n {value}"
                    # await push_output_to_terminal(task_response.get("data", ""))
                    # temp push dict to terminal for debugging
                    # data_type = value.get("type")
                    # data_value = value.get("value")

                    # error is a special case, push to error stream
                    if key == "error":
                        await push_error_to_terminal(value)
                        continue

                    await push_output_to_terminal(f"--- {key} ---")
                    await push_output_to_terminal(value)
                    # # then, print out the rest as needed.
                    # if data_type == "text":
                    #     await push_output_to_terminal(f"--- {key} ---")

                    #     await push_output_to_terminal(value)

                    # if data_type == "bytes":
                    #     await push_output_to_terminal(value)
                    # change to push_hex_output to term or something

                new_last_uuid = task.get("task_uuid")

        last_uuid = new_last_uuid

    # command history
    # Initialize history for this session if missing
    if implant_uuid not in command_history:
        command_history[implant_uuid] = []
        history_index[implant_uuid] = -1

    def navigate_history(direction):
        hist = command_history[implant_uuid]
        idx = history_index[implant_uuid]

        if not hist:
            return

        if direction == "up":
            idx = max(0, idx - 1) if idx != -1 else len(hist) - 1
        elif direction == "down":
            idx = min(len(hist), idx + 1)

        history_index[implant_uuid] = idx

        if 0 <= idx < len(hist):
            ui_user_input.value = hist[idx]
        else:
            ui_user_input.value = ""  # Clear if we go past the end

    # --- INIT ---
    async def setup_terminal():
        task_history = await get_implant_task_history(implant_uuid)
        if task_history:
            tasks = task_history.get("data") or []
            if isinstance(tasks, list):
                await add_tasks_to_terminal(tasks)

        await push_output_to_terminal("--- SESSION ESTABLISHED ---")

        # Scroll to bottom
        ui.run_javascript(
            """
            const logElement = document.querySelector('.q-scrollarea__content');
            if (logElement && logElement.lastElementChild) { logElement.lastElementChild.scrollIntoView(); }
        """
        )

    await setup_terminal()

    update_time = app.storage.user.get("auto_refresh_rate", 1)
    ui.timer(update_time, update_terminal)
