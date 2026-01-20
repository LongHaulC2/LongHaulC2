import logging
from pathlib import Path

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
    # 1. Full Screen Layout Setup
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Listeners")

    await listener_view()


async def listener_view():
    """
    Listener View
    """
    # Keep track of state
    previous_ids = set()
    table_initialized = False

    # --- MAIN GLASS PANEL ---
    # Using 'tech-glass-panel' from CSS to handle the visuals (Glass/Border/Shadow)
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):

        # --- HEADER BAR ---
        # Matches Payloads style
        with ui.row().classes("w-full items-center justify-between tech-header-bar"):

            # Left: Title
            with ui.row().classes("items-center gap-3"):
                ui.icon("rss_feed", color="emerald-500").classes("text-xl")
                ui.label("LISTENERS //").classes("tech-label-title")

            # Right: Controls
            with ui.row().classes("items-center gap-2"):

                # ADD BUTTON
                with ui.button(on_click=start_listener_dialogue).classes(
                    "tech-btn-action px-3"
                ).props("flat no-caps dense"):
                    ui.icon("add", size="xs").classes("mr-2")
                    ui.label("NEW").classes("text-xs font-bold tracking-wide")
                    ui.tooltip("Spawn new listener")

                # REFRESH
                ui.button(icon="refresh", on_click=lambda: refresh()).props(
                    "dense flat size=sm"
                ).classes("tech-btn-ghost").tooltip("Force Refresh")

                # STOP
                ui.button(icon="stop", on_click=lambda: stop_listeners()).props(
                    "dense flat size=sm"
                ).classes("text-red-400 hover:text-red-200 transition-colors").tooltip(
                    "Stop Selected Listeners"
                )

        # --- TABLE AREA ---
        # Fills remaining height, no padding around table so it hits the edges
        with ui.column().classes("w-full flex-grow relative overflow-hidden"):

            table = (
                ui.table(
                    columns=[],  # filled later
                    rows=[],
                    row_key="listener_uuid",
                    selection="multiple",
                    pagination=100,
                )
                # TABLE STYLING:
                # bg-transparent: Blends into the main glass panel
                # no-shadow: Removes card look
                # text-neutral-300: Ensures text is readable on dark bg
                .classes(
                    "w-full h-full no-shadow bg-transparent text-neutral-300"
                ).props("dense flat virtual-scroll square")
            )

    # --- LOGIC ---

    async def refresh():
        nonlocal previous_ids
        nonlocal table_initialized

        data = await get_all_listener_data()
        data = data.get("data")
        if not data:
            server_log.debug("No data from listeners")
            return

        # Build columns only once
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
                if key != "listener_profile_contents"  # Exclude large content
            ]

            # HTML Rendering Slot for Notes
            table.add_slot(
                "body-cell-notes",
                """
                <q-td :props="props">
                    <div style="max-height: 20px; max-width: 300px; overflow: hidden; word-wrap: break-word; white-space: normal;" class="opacity-70 text-xs font-mono"> 
                        <span v-if="props.row.notes" v-html="props.row.notes"></span>
                    </div>
                </q-td>
                """,
            )

            # Custom Header Styling (Tech Look) to match the dark theme
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

    async def stop_listeners():
        selected_listeners_uuids = [row["listener_uuid"] for row in table.selected]
        if not selected_listeners_uuids:
            ui.notify("No listeners selected", type="warning", color="orange-9")
            return

        for listener_uuid in selected_listeners_uuids:
            await stop_listener(listener_uuid)

        await refresh()
        ui.notify(
            f"Stopped {len(selected_listeners_uuids)} listeners",
            type="info",
            color="grey-8",
        )

    # Start Timer
    ui.timer(3, refresh)
    # Initial load
    await refresh()


async def start_listener_dialogue():

    async def _start_listener():
        file_path = (
            Path(__file__).resolve().parent.parent
            / "user"
            / "profiles"
            / str(listener_profile_field.value)
        )

        if not file_path.exists():
            ui.notify(f"Malleable profile not found: {file_path.name}", type="warning")
            return

        listener_host = listener_host_field.value
        listener_port = listener_port_field.value
        listener_type = listener_type_field.value
        listener_name = listener_name_field.value
        listener_notes = listener_notes_field.value
        listener_profile_name = listener_profile_field.value
        listener_profile_contents = get_malleable_profile_content(file_path)

        if not all([listener_host, listener_port, listener_type, listener_name]):
            ui.notify("Missing required fields", type="warning", color="orange-9")
            return

        dialog_spinner.visible = True

        result = await start_listener(
            listener_host=listener_host,
            listener_port=int(listener_port),
            listener_type=listener_type,
            listener_name=listener_name,
            listener_notes=listener_notes,
            listener_profile_name=listener_profile_name,
            listener_profile_contents=listener_profile_contents,
        )

        dialog_spinner.visible = False

        if not result:
            ui.notify("Failed to start listener", type="negative")
            return

        ui.notify("Listener started successfully", type="positive", color="emerald-9")
        dialog.close()

    # --- TECH DIALOG ---
    # Using 'tech-dialog' class for styling
    with ui.dialog() as dialog, ui.card().classes(
        "tech-dialog w-[600px] p-0 rounded overflow-hidden"
    ):

        # Header
        with ui.row().classes(
            "w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"
        ):
            with ui.row().classes("gap-2 items-center"):
                ui.icon("rocket_launch", color="emerald-500")
                ui.label("SPAWN_LISTENER").classes(
                    "text-sm font-bold tracking-widest text-emerald-500 font-mono"
                )
            ui.button(icon="close", on_click=dialog.close).props(
                "dense flat size=sm color=grey"
            )

        # Body
        with ui.column().classes("p-6 gap-6 w-full"):

            # Name & Type
            with ui.row().classes("w-full gap-4"):
                listener_name_field = (
                    ui.input("NAME")
                    .props("outlined dense dark color=emerald")
                    .classes("flex-1")
                )
                listener_type_field = (
                    ui.select(["http", "ntp"], label="TYPE", value="http")
                    .props("outlined dense dark color=emerald options-dense")
                    .classes("flex-1")
                )

            # Host & Port
            with ui.row().classes("w-full gap-4"):
                listener_host_field = (
                    ui.input("HOST")
                    .props("outlined dense dark color=emerald")
                    .classes("flex-1")
                )
                with listener_host_field:
                    ui.tooltip("External IP/Hostname. Do NOT use 0.0.0.0")

                listener_port_field = (
                    ui.input(
                        label="PORT",
                        placeholder="1–65535",
                        validation={
                            "Invalid": lambda v: v.isdigit() and 1 <= int(v) <= 65535,
                        },
                    )
                    .props(
                        "outlined dense dark type=number min=1 max=65535 color=emerald"
                    )
                    .classes("w-32")
                )

            # Notes
            listener_notes_field = (
                ui.textarea("NOTES")
                .props("outlined autogrow dark color=emerald")
                .classes("w-full")
            )

            # Profile
            listener_profile_field = (
                ui.select(
                    get_malleable_profiles_list(),
                    label="C2 PROFILE",
                    with_input=True,
                )
                .props("outlined dense dark color=emerald options-dense")
                .classes("w-full")
            )

        # Footer
        with ui.row().classes(
            "w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"
        ):
            # Spinner
            dialog_spinner = ui.spinner(size="sm")
            dialog_spinner.visible = False

            ui.button("CANCEL", on_click=dialog.close).props(
                "flat dense color=grey no-caps"
            )

            ui.button("INITIALIZE", on_click=_start_listener).props(
                "unelevated dense color=emerald text-color=white no-caps"
            ).classes("font-bold tracking-wide")

    dialog.open()


def get_malleable_profiles_list() -> list:
    try:
        script_path = Path(__file__).resolve().parent.parent / "user" / "profiles"
        script_path.mkdir(parents=True, exist_ok=True)
        list_of_mc2_profiles = sorted(
            (p.name for p in script_path.iterdir() if p.is_file()),
            key=str.lower,
        )
        return list_of_mc2_profiles
    except Exception as e:
        server_log.error(e)
        return []


def get_malleable_profile_content(file_path) -> str:
    try:
        with open(file_path, "r") as file:
            return file.read()
    except Exception as e:
        server_log.error(e)
        return ""
