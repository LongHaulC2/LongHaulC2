import logging
from itertools import groupby
from pathlib import Path

import httpx
from nicegui import ui
from nicegui.events import KeyEventArguments

# --- Imports ---
from client.src.client.modules.api_calls import (
    get_all_listener_data,
    start_listener,
    stop_listener,
)
from client.src.client.pages.menu import setup_menu
from client.src.client.style import BUTTON_COLOR, TEXT_COLOR

server_log = logging.getLogger("server")
server_log.info("Loading /listeners page")


# ==============================================================================
#   UI HELPERS
# ==============================================================================
def stat_widget(label: str, value: str, icon: str, color: str = "emerald"):
    """Creates a small tech-styled stat card"""
    with ui.card().classes(
        "flex-1 min-w-[150px] p-3 gap-1 bg-white/5 border border-white/10 rounded-sm no-shadow"
    ):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(label).classes(
                "text-[10px] font-mono tracking-widest text-neutral-500 uppercase"
            )
            ui.icon(icon, size="xs", color=f"{color}-500").classes("opacity-80")
        ui.label(str(value)).classes(
            "text-xl font-bold font-mono tracking-wide text-neutral-200 truncate"
        )


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
    Listener View Dashboard
    """

    # --- MAIN GLASS PANEL ---
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):

        # --- HEADER BAR ---
        with ui.row().classes("w-full items-center justify-between tech-header-bar"):
            # Left: Title
            with ui.row().classes("items-center gap-3"):
                ui.icon("rss_feed", color="emerald-500").classes("text-xl")
                ui.label("INFRASTRUCTURE // LISTENERS").classes("tech-label-title")

            # Right: Controls
            with ui.row().classes("items-center gap-2"):
                # ADD BUTTON
                with ui.button(on_click=start_listener_dialogue).classes(
                    "tech-btn-action px-3"
                ).props("flat no-caps dense"):
                    ui.icon("add", size="xs").classes("mr-2")
                    ui.label("LISTENER").classes("text-xs font-bold tracking-wide")

                # REFRESH
                ui.button(
                    icon="refresh", on_click=lambda: ui.navigate.to("/listeners")
                ).props("dense flat size=sm").classes("tech-btn-ghost")

        # --- CONTENT AREA ---
        with ui.column().classes("w-full flex-grow p-6 gap-6 overflow-hidden"):

            # Fetch Data
            data_resp = await get_all_listener_data()
            listener_data = data_resp.get("data", [])

            # --- 1. TELEMETRY CARDS ---
            total_count = len(listener_data)
            http_count = len(
                [l for l in listener_data if l.get("listener_type") == "http"]
            )
            active_count = len(
                [l for l in listener_data if l.get("active", True)]
            )  # Default true for now

            with ui.row().classes("w-full gap-4"):
                stat_widget("TOTAL listenerS", str(total_count), "router", "emerald")
                stat_widget("ONLINE", str(active_count), "wifi", "green")
                stat_widget("HTTP AGENTS", str(http_count), "public", "blue")

            # --- 2. MAIN TABLE AREA ---
            with ui.card().classes(
                "w-full flex-grow bg-white/5 border border-white/5 p-0 rounded overflow-hidden flex flex-col"
            ):
                if not listener_data:
                    with ui.column().classes(
                        "w-full h-full items-center justify-center opacity-30"
                    ):
                        ui.icon("router", size="4em")
                        ui.label("NO ACTIVE LISTENERS").classes(
                            "font-mono text-sm mt-2"
                        )
                else:
                    await render_listeners_table(listener_data)


async def render_listeners_table(data: list):
    """Renders the list of listeners in a dashboard table"""

    # Prepare Rows
    table_rows = []
    for l in data:
        bind_addr = f"{l.get('listener_host', '0.0.0.0')}:{l.get('listener_port', '0')}"

        # Check active status (Defaults to True if key missing, assuming API returns valid list)
        is_active = l.get("active", True)

        table_rows.append(
            {
                "id": l.get("listener_uuid"),
                "status": is_active,  # Boolean for the visual slot
                "name": l.get("listener_name", "Unknown"),
                "type": l.get("listener_type", "http"),
                "bind": bind_addr,
                "profile": l.get("listener_profile_name", "Default"),
                "notes": l.get("listener_notes", ""),
                "listener_uuid": l.get("listener_uuid"),
            }
        )

    # Search Bar Logic
    filter_text = (
        ui.input(placeholder="SEARCH LISTENERS...")
        .props("outlined dense dark color=emerald input-class=text-xs")
        .classes("m-3 w-96")
    )

    # Define Columns
    columns = [
        {
            "name": "name",
            "label": "listener NAME",
            "field": "name",
            "align": "left",
            "sortable": True,
        },
        {
            "name": "type",
            "label": "PROTOCOL",
            "field": "type",
            "align": "left",
            "sortable": True,
        },
        {
            "name": "bind",
            "label": "BIND ADDRESS",
            "field": "bind",
            "align": "left",
            "sortable": True,
        },
        {
            "name": "profile",
            "label": "C2 PROFILE",
            "field": "profile",
            "align": "left",
            "sortable": True,
        },
        {"name": "notes", "label": "NOTES", "field": "notes", "align": "left"},
        {
            "name": "status",
            "label": "STATUS",
            "field": "status",
            "align": "left",
            "sortable": True,
        },
    ]

    # Render Table
    table = (
        ui.table(
            columns=columns,
            rows=table_rows,
            row_key="id",
            selection="multiple",
            pagination=15,
        )
        .classes("w-full bg-transparent no-shadow text-neutral-300")
        .bind_filter_from(filter_text, "value")
    )

    # --- CUSTOM SLOTS ---

    # Header Styling
    table.add_slot(
        "header",
        r"""
        <q-tr :props="props" class="bg-black/20 text-neutral-500 uppercase text-[10px] font-bold tracking-widest border-b border-white/10">
            <q-th auto-width />
            <q-th v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.label }}
            </q-th>
        </q-tr>
    """,
    )

    # STATUS SLOT (The requested visual)
    # v-if checks the boolean value of the row.
    table.add_slot(
        "body-cell-status",
        r"""
        <q-td :props="props">
            <div v-if="props.value" class="row items-center gap-2">
                <div class="relative flex items-center justify-center">
                    <div class="w-2 h-2 rounded-full bg-emerald-400 absolute animate-pulse"></div>
                    <div class="w-1.5 h-1.5 rounded-full bg-emerald-400"></div>
                </div>
                <span class="text-[10px] font-bold text-emerald-400 tracking-wider">ONLINE</span>
            </div>
            
            <div v-else class="row items-center gap-2 opacity-50">
                <div class="w-1.5 h-1.5 rounded-full bg-red-500"></div>
                <span class="text-[10px] font-bold text-red-500 tracking-wider">OFFLINE</span>
            </div>
        </q-td>
    """,
    )

    # Protocol Badge Slot
    table.add_slot(
        "body-cell-type",
        r"""
        <q-td :props="props">
            <q-badge :color="props.value === 'http' ? 'blue-9' : props.value === 'ntp' ? 'purple-9' : 'grey-8'" 
                     text-color="white" :label="props.value.toUpperCase()" 
                     class="font-mono text-[10px] px-2 py-0.5 rounded-sm shadow-sm" />
        </q-td>
    """,
    )

    # Bind Address Slot
    table.add_slot(
        "body-cell-bind",
        r"""
        <q-td :props="props">
            <div class="row items-center gap-2 font-mono text-xs text-emerald-400">
                <q-icon name="lan" size="xs" class="opacity-70" />
                {{ props.value }}
            </div>
        </q-td>
    """,
    )

    # Notes Slot
    table.add_slot(
        "body-cell-notes",
        r"""
        <q-td :props="props">
            <div style="max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" 
                 class="opacity-60 text-xs italic">
                {{ props.value }}
            </div>
        </q-td>
    """,
    )

    # Footer Controls
    with ui.row().classes(
        "w-full p-2 justify-end border-t border-white/5 bg-red-900/5"
    ):

        async def stop_selected():
            selected_rows = table.selected
            if not selected_rows:
                ui.notify("No listeners selected", type="warning", color="orange-9")
                return

            count = len(selected_rows)
            for row in selected_rows:
                await stop_listener(row["listener_uuid"])

            ui.notify(f"Terminated {count} listeners", type="negative")
            ui.navigate.to("/listeners")

        ui.button("TERMINATE SELECTED", icon="stop", on_click=stop_selected).props(
            "flat dense color=red no-caps size=sm"
        ).classes("font-bold tracking-wide hover:bg-red-900/20")


# ==============================================================================
#   DIALOG LOGIC
# ==============================================================================
async def start_listener_dialogue():

    async def _start_listener():
        if not all(
            [
                listener_host_field.value,
                listener_port_field.value,
                listener_name_field.value,
            ]
        ):
            ui.notify("Missing required fields", type="warning", color="orange-9")
            return

        file_path = (
            Path(__file__).resolve().parent.parent
            / "user"
            / "profiles"
            / str(listener_profile_field.value)
        )

        if not file_path.exists():
            ui.notify(f"Profile not found: {file_path.name}", type="warning")
            return

        dialog_spinner.visible = True

        result = await start_listener(
            listener_host=listener_host_field.value,
            listener_port=int(listener_port_field.value),
            listener_type=listener_type_field.value,
            listener_name=listener_name_field.value,
            listener_notes=listener_notes_field.value,
            listener_profile_name=listener_profile_field.value,
            listener_profile_contents=get_malleable_profile_content(file_path),
        )

        dialog_spinner.visible = False

        if result:
            ui.notify("Listener Online", type="positive", color="emerald-9")
            dialog.close()
            # ui.navigate.to("/listeners")
        else:
            ui.notify("Failed to start listener", type="negative")

    # --- TECH DIALOG ---
    with ui.dialog() as dialog, ui.card().classes(
        "tech-dialog w-[600px] p-0 rounded overflow-hidden"
    ):
        with ui.row().classes(
            "w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"
        ):
            with ui.row().classes("gap-2 items-center"):
                ui.icon("rocket_launch", color="emerald-500")
                ui.label("INITIALIZE_listener").classes(
                    "text-sm font-bold tracking-widest text-emerald-500 font-mono"
                )
            ui.button(icon="close", on_click=dialog.close).props(
                "dense flat size=sm color=grey"
            )

        with ui.column().classes("p-6 gap-6 w-full"):
            with ui.row().classes("w-full gap-4"):
                listener_name_field = (
                    ui.input("LISTENER NAME")
                    .props("outlined dense dark color=emerald")
                    .classes("flex-1")
                )

                listener_type_field = (
                    ui.select(["http", "ntp"], label="PROTOCOL", value="http")
                    .props("outlined dense dark color=emerald options-dense")
                    .classes("w-1/3")
                )

            with ui.row().classes("w-full gap-4"):
                listener_host_field = (
                    ui.input("BIND HOST")
                    .props("outlined dense dark color=emerald")
                    .classes("flex-1")
                )
                with listener_host_field:
                    ui.tooltip("External IP/Hostname (No 0.0.0.0)")

                listener_port_field = (
                    ui.input(
                        label="PORT",
                        placeholder="80",
                        validation={
                            "Invalid": lambda v: v.isdigit() and 1 <= int(v) <= 65535
                        },
                    )
                    .props("outlined dense dark type=number color=emerald")
                    .classes("w-32")
                )

            listener_profile_field = (
                ui.select(
                    get_malleable_profiles_list(),
                    label="MALLEABLE PROFILE",
                    with_input=True,
                )
                .props("outlined dense dark color=emerald options-dense")
                .classes("w-full")
            )

            listener_notes_field = (
                ui.textarea("OPERATIONAL NOTES")
                .props(
                    "outlined dark color=emerald input-class='h-32 resize-none'"
                )  # Apply height directly to input
                .classes("w-full")  # Keep width on the wrapper
            )

        with ui.row().classes(
            "w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"
        ):
            dialog_spinner = ui.spinner(size="sm", color="emerald-500")
            dialog_spinner.visible = False

            ui.button("CANCEL", on_click=dialog.close).props(
                "flat dense color=grey no-caps"
            )

            ui.button("SPAWN LISTENER", on_click=_start_listener).props(
                "unelevated dense color=emerald text-color=white no-caps"
            ).classes("font-bold tracking-wide")

    dialog.open()


def get_malleable_profiles_list() -> list:
    try:
        script_path = Path(__file__).resolve().parent.parent / "user" / "profiles"
        script_path.mkdir(parents=True, exist_ok=True)
        return sorted(
            (p.name for p in script_path.iterdir() if p.is_file()), key=str.lower
        )
    except Exception:
        return []


def get_malleable_profile_content(file_path) -> str:
    try:
        with open(file_path, "r") as file:
            return file.read()
    except Exception:
        return ""
