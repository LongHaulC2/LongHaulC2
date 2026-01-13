import logging

import httpx
from nicegui import ui
from nicegui.events import KeyEventArguments

from client.src.client.modules.api_calls import (
    get_all_implant_data,
    get_all_listener_data,
    get_implant_task_history,
    get_implant_task_history_since_uuid,
    get_listener_data,
    queue_task,
    start_listener,
    stop_listener,
    update_implant,
)
from client.src.client.modules.task_definitions import ResultType, task_tree
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

server_log.info("Loading /listeners page")


@ui.page("/listeners")
async def listeners():
    # HEY- readme: This is a hack to get the page full screen (and make h-full work). It should also allow for things like headers to fit without adjusting it manually
    # see the link below.
    # https://github.com/zauberzeug/nicegui/discussions/4049
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    ui.context.client.content.classes("h-full")

    setup_menu("Listeners")

    await listener_view()


async def listener_view():
    """
    Listener View

    Creates the table for on screen, initially blank.

    Then, every 1 seconds, gets the new API data, and udpates the table based on it.
    """

    # Keep track of previous implant IDs
    previous_ids = set()
    table_initialized = False  # track if table columns are already built. Solves the bug of saying that every implant in the table is a new connection

    # Setup header
    with ui.row().classes("w-full items-center justify-between"):
        # LEFT: title / context
        ui.label("Listeners").classes(f"text-h6 dense {TEXT_COLOR}")

        with ui.row().classes("items-center q-gutter-xs"):

            # RIGHT: action buttons
            with ui.row().classes("items-center q-gutter-xs"):

                with ui.button(
                    icon="add", on_click=lambda: start_listener_dialogue()
                ).props("dense flat round").classes(f"[&_.q-icon]:{ICON_COLOR}"):
                    ui.tooltip("Add listener")

                with ui.button(icon="refresh", on_click=lambda: refresh()).props(
                    "dense flat round"
                ).classes(f"[&_.q-icon]:{ICON_COLOR}"):
                    ui.tooltip("Force Refresh listeners table")

                with ui.button(icon="stop", on_click=lambda: stop_listeners()).props(
                    "dense flat round"
                ).classes(f"[&_.q-icon]:{ICON_COLOR}"):
                    ui.tooltip("Stop listener")

    ui.separator()

    table = (
        ui.table(
            columns=[],  # filled later
            rows=[],
            row_key="listener_uuid",
            selection="multiple",
            # on_select=lambda e: ui.notify(f"selected: {e.selection}"),
            pagination=100,
        )
        .classes(f"w-full no-shadow {TEXT_COLOR}")
        .props("dense virtual-scroll")
        # virtual scroll only renders items on screen. Helpful when a large amount of items exist in the table.
    )

    async def refresh():
        nonlocal previous_ids  # use the variable above that's in the implant_view scope, to track listener_uuid's between calls
        nonlocal table_initialized  # track if table columns are already built. Solves the bug of saying that every implant in the table is a new connection

        data = await get_all_listener_data()
        data = data.get("data")
        if not data:
            server_log.debug("No data from listeners")
            return

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
        ids = [row["listener_uuid"] for row in table.selected]

        if not ids:
            ui.notify("No rows selected", color="warning")
            return

        for listener_uuid in ids:
            # do request
            await delete_implant(listener_uuid=listener_uuid)

            # bug, rows are still "checked" after deleting

    # async def handle_notes():
    #     # get all selected
    #     ids = [row["llistener_uuid"] for row in table.selected]
    #     # if selected = 1, pull up notes from that agent and populate editor with them

    #     if len(ids) == 1:
    #         listener_uuid = ids[0]
    #         # lookup server value of notes, NOT what's currently in the table. Server is source of truth
    #         implant_data = await get_list(listener_uuid=listener_uuid)
    #         implant_notes = implant_data.get("data", {}).get("notes")

    #         # get notes from dialog
    #         notes = await open_notes_dialog(
    #             implant_uuid == f"ID: {listener_uuid}",
    #             populate_editor_with=implant_notes,
    #         )

    #         data = {"notes": notes}
    #         # post to update implant
    #         # NOT IMPLEMENTED YET
    #         await update_implant(listener_uuid=listener_uuid, data=data)

    #     elif len(ids) > 1:
    #         notes = await open_notes_dialog(
    #             listener_uuid=f"Editing {len(ids)} implants notes"
    #         )
    #         # ui.notify(notes)
    #         # post to update all the implants
    #         data = {"notes": notes}

    #         for listener_uuid in ids:
    #             await update_implant(listener_uuid=listener_uuid, data=data)

    #     else:
    #         ui.notify("Please select an implant to edit its notes")
    #     #

    async def stop_listeners():
        # get all  selected
        selected_listeners_uuids = [row["listener_uuid"] for row in table.selected]

        for listener_uuid in selected_listeners_uuids:
            await stop_listener(listener_uuid)

        # call refresh
        await refresh()

    async def start_listener_dialogue():

        with ui.dialog() as dialog:
            with ui.card().classes("w-[600px] max-w-full p-6 space-y-4"):

                # Header
                ui.label("Spawn a Listener").classes(
                    "text-xl font-semibold text-center"
                )

                ui.separator()

                # Name + Type (row)
                with ui.row().classes("w-full gap-4"):
                    listener_name_field = ui.input("Name").classes("flex-1")

                    listener_type_field = ui.select(
                        ["http", "ntp"],
                        label="Type [only HTTP]",
                    ).classes("flex-1")

                # Host + Port (row)
                with ui.row().classes("w-full gap-4"):
                    listener_host_field = ui.input("Host [IP, or DNS Name]").classes(
                        "flex-1"
                    )

                    listener_port_field = (
                        ui.input(
                            label="Port",
                            placeholder="1–65535",
                            validation={
                                "Port must be a number": lambda v: v.isdigit(),
                                "Port must be between 1 and 65535": lambda v: v.isdigit()
                                and 1 <= int(v) <= 65535,
                            },
                        )
                        .props("type=number min=1 max=65535")
                        .classes("w-32")
                    )

                ui.separator()

                # Notes (multiline)
                listener_notes_field = (
                    ui.textarea("Notes").classes("w-full").props("rows=3")
                )

                # Profile (dropdown or paste)
                listener_profile_field = ui.select(
                    ["default", "stealth", "debug"],
                    label="Profile [not implemented]",
                    with_input=True,
                ).classes("w-full")

                ui.separator()

                # Actions
                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button("Cancel", on_click=dialog.close).props("flat")
                    ui.button(
                        "Spawn Listener",
                        color="primary",
                        on_click=lambda: _start_listener(),
                    )  # on click to new func

        async def _start_listener():
            # pull values
            listener_host = listener_host_field.value
            listener_port = listener_port_field.value
            listener_type = listener_type_field.value
            listener_name = listener_name_field.value
            listener_notes = listener_notes_field.value
            listener_profile = listener_profile_field.value

            check_type(listener_host, str, "listener_host")
            check_type(listener_port, int, "listener_port")
            check_type(listener_type, str, "listener_type")
            check_type(listener_name, str, "listener_name")
            check_type(listener_notes, str, "listener_notes")
            check_type(listener_profile, str, "listener_profile")

            result = await start_listener(
                listener_host=listener_host,
                listener_port=int(listener_port),
                listener_type=listener_type,
                listener_name=listener_name,
                listener_notes=listener_notes,
                listener_profile=listener_profile,
            )

            if not result:
                ui.notification("Listener could not be started!", type="negative")
                return
            ui.notification("Listener started!", type="positive")
            # refresh on creation
            await refresh()

            # success/fail message

        # send req

        result = await dialog

    # set to every 3 seconds, less load on server.
    ui.timer(3, refresh)
