import logging
from itertools import groupby
from pathlib import Path

import httpx
from nicegui import ui
from nicegui.events import KeyEventArguments

# --- Keep your original imports ---
from client.src.client.modules.api_calls import (
    build_implant,
    get_all_implant_data,
    get_all_listener_data,
    get_implant_task_history,
    get_implant_task_history_since_uuid,
    get_listener_data,
    get_payload_bytes,
    get_payload_data,
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

# ==============================================================================
#   THE "REFINED TECH" CSS THEME
#   (Radius set to 4px - "Just enough to remove the edge")
# ==============================================================================
TECH_CSS = r"""
/* --- 1. GLOBAL SCROLLBAR --- */
.tech-scroll ::-webkit-scrollbar { width: 6px; height: 6px; }
.tech-scroll ::-webkit-scrollbar-track { background: transparent; }
.tech-scroll ::-webkit-scrollbar-thumb { background: #3f3f46; border-radius: 3px; }
.tech-scroll ::-webkit-scrollbar-thumb:hover { background: #52525b; }

/* --- 2. THE TECH EXPANSION ITEM --- */
.tech-expansion {
    background-color: rgba(23, 23, 23, 0.4); 
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 4px; /* SUBTLE RADIUS */
    margin-bottom: 8px;
    transition: all 0.2s ease;
}
.tech-expansion:hover {
    border-color: rgba(255, 255, 255, 0.1);
    background-color: rgba(23, 23, 23, 0.6);
}
/* Active State */
.tech-expansion.q-expansion-item--expanded {
    background-color: rgba(23, 23, 23, 0.9);
    border-color: rgba(52, 211, 153, 0.4); /* Emerald Border */
    box-shadow: 0 4px 20px -10px rgba(16, 185, 129, 0.1);
}
.tech-expansion.q-expansion-item--expanded > .q-expansion-item__container > .q-item {
    color: #34d399 !important;
}
.tech-expansion .q-focus-helper { display: none !important; }

/* --- 3. THE EXPANSION CONTENT --- */
.tech-expansion .q-expansion-item__content {
    background-color: rgba(0, 0, 0, 0.2);
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    padding: 0 !important;
}

/* --- 4. THE FLUSH EMBEDDED TABLE --- */
.tech-table-flush .q-table__card,
.tech-table-flush .q-table__container {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important; /* Keep internal table square to fit container */
    width: 100% !important;
    margin: 0 !important;
}
.tech-table-flush .q-table__top { display: none !important; }

.tech-table-flush thead tr, .tech-table-flush th {
    background-color: rgba(0, 0, 0, 0.3) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
    color: #71717a;
    height: 32px;
}
.tech-table-flush tbody td {
    border-bottom: 1px solid rgba(255, 255, 255, 0.03) !important;
    height: 40px;
    font-size: 0.85rem;
    color: #d4d4d8;
}
.tech-table-flush tbody tr:last-child td { border-bottom: none !important; }

/* --- 5. DIALOGS --- */
.tech-dialog {
    background-color: #18181b !important;
    border: 1px solid rgba(52, 211, 153, 0.2);
    box-shadow: 0 0 40px rgba(0,0,0,0.5);
    border-radius: 4px !important; /* SUBTLE RADIUS */
}
"""


@ui.page("/payloads")
async def payloads():
    ui.add_head_html(f"<style>{TECH_CSS}</style>")

    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    ui.context.client.content.classes("h-full")

    setup_menu("Payloads")
    await payloads_view()


async def payloads_view():

    # --- 1. THE MAIN GLASS PANEL (Rounded Corners) ---
    # Changed rounded-none to rounded (4px)
    with ui.card().classes(
        "w-full h-full p-0 flex flex-col gap-0 "
        "bg-neutral-900/60 backdrop-blur-md border border-white/5 rounded overflow-hidden shadow-2xl"
    ):

        # --- 2. HEADER BAR ---
        with ui.row().classes(
            "w-full px-6 py-4 items-center justify-between bg-white/5 border-b border-white/5"
        ):
            # Left: Title
            with ui.row().classes("items-center gap-3"):
                ui.icon("layers", color="emerald-500").classes("text-xl")
                ui.label("PAYLOAD_LIBRARY //").classes(
                    "text-sm font-bold tracking-widest text-neutral-400 font-mono"
                )

            # Right: Actions
            with ui.row().classes("items-center gap-2"):
                # "Build" Button - Removed 'square' prop (defaults to 4px)
                with ui.button(on_click=start_payload_dialogue).classes(
                    "border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 px-4 transition-all"
                ).props("flat no-caps dense"):
                    ui.icon("add_circle", size="xs").classes("mr-2")
                    ui.label("COMPILE NEW").classes("text-xs font-bold tracking-wide")

                # "Refresh" Button
                ui.button(icon="refresh", on_click=lambda: ui.open("/payloads")).props(
                    "dense flat size=sm"
                ).classes("text-neutral-500 hover:text-white transition-colors")

        # --- 3. SCROLLABLE CONTENT AREA ---
        with ui.scroll_area().classes("w-full flex-grow p-6 tech-scroll"):

            payload_data_response = await get_payload_data()
            payload_data = payload_data_response.get("data", [])

            if not payload_data:
                with ui.column().classes(
                    "w-full h-64 items-center justify-center opacity-30"
                ):
                    ui.icon("inbox", size="4em")
                    ui.label("NO ARTIFACTS FOUND").classes("font-mono text-sm mt-2")
            else:
                await render_payloads(payload_data=payload_data)


async def render_payloads(payload_data: dict):

    columns = [
        {"name": "name", "label": "Artifact", "field": "name", "align": "left"},
        {
            "name": "hash",
            "label": "Checksum (MD5)",
            "field": "hash",
            "align": "left",
            "classes": "font-mono text-xs opacity-70",
        },
        {"name": "actions", "label": "Op", "field": "actions", "align": "right"},
    ]

    sorted_data = sorted(
        payload_data, key=lambda x: x.get("payload_listener_uuid", "Unknown")
    )
    grouped_payloads = {}
    for key, group in groupby(
        sorted_data, key=lambda x: x.get("payload_listener_uuid", "Unknown")
    ):
        grouped_payloads[key] = list(group)

    async def handle_download(e):
        row = e.args
        ui.notify(f"Retrieving {row['name']}...", type="info", color="grey-9")
        file_bytes = await get_payload_bytes(row["hash"])
        if file_bytes:
            ui.download(file_bytes, filename=row["name"])
            ui.notify("Transfer Complete", type="positive")
        else:
            ui.notify("Transfer Failed", type="negative")

    for listener_uuid, payloads in grouped_payloads.items():
        table_rows = []
        for p in payloads:
            table_rows.append(
                {
                    "id": p.get("id"),
                    "name": p.get("payload_name", "Unnamed"),
                    "hash": p.get("payload_hash", ""),
                    "uuid": listener_uuid,
                }
            )

        listener_data = await get_listener_data(listener_uuid)
        listener_name = listener_data.get("data", {}).get("listener_name", "Unknown")

        # Tech Expansion (CSS handles 4px radius)
        with ui.expansion().classes("w-full tech-expansion group") as expansion:

            with expansion.add_slot("header"):
                with ui.row().classes("w-full items-center py-2 px-1"):
                    ui.icon("dns", size="sm").classes(
                        "mr-4 text-neutral-600 group-hover:text-emerald-400 transition-colors"
                    )
                    with ui.column().classes("gap-0"):
                        ui.label(listener_name).classes(
                            "text-sm font-bold text-neutral-200 tracking-wide uppercase"
                        )
                        ui.label(f"UUID: {listener_uuid[:8]}...").classes(
                            "text-xs font-mono text-neutral-600"
                        )
                    ui.space()

                    # Badge count - Rounded
                    with ui.row().classes("items-center gap-2"):
                        ui.label(f"{len(table_rows)} ITEMS").classes(
                            "text-[10px] font-bold text-neutral-600 bg-black/20 px-2 py-1 rounded-sm"
                        )

            table = ui.table(columns=columns, rows=table_rows, row_key="id").classes(
                "tech-table-flush"
            )

            # Download Button - Removed 'square'
            table.add_slot(
                "body-cell-actions",
                r"""
                <q-td :props="props">
                    <q-btn icon="download" flat dense size="sm" color="grey-5" 
                           class="hover:text-emerald-400 transition-colors"
                           @click="$parent.$emit('download', props.row)">
                        <q-tooltip class="bg-neutral-900 text-xs">DOWNLOAD ARTIFACT</q-tooltip>
                    </q-btn>
                </q-td>
                """,
            )
            table.on("download", handle_download)


async def start_payload_dialogue():

    VARIANT_MAP = {"http": ["http_wininet"]}
    response = await get_all_listener_data()
    listeners_list = response.get("data", [])
    listener_type_map = {l["listener_name"]: l["listener_type"] for l in listeners_list}
    listener_uuid_map = {l["listener_name"]: l["listener_uuid"] for l in listeners_list}

    async def _build_implant():
        name = name_input.value
        listener_name = listener_select.value
        variant = variant_select.value
        fmt = format_select.value

        if not all([name, listener_name, fmt]):
            ui.notify("MISSING REQUIRED FIELDS", type="warning", color="orange-9")
            return

        build_btn.props("loading")

        listener_uuid = listener_uuid_map.get(listener_name)
        result = await build_implant(
            implant_name=name,
            implant_listener_uuid=listener_uuid,
            implant_variant=variant if variant_select.visible else None,
            output_format=fmt,
        )

        build_btn.props("loading=false")

        if not result:
            ui.notify("COMPILATION FAILED", type="negative")
            return

        ui.notify(f"BUILD STARTED: {name}.{fmt}", type="positive", color="emerald-9")
        dialog.close()

    def _on_listener_change(e):
        selected_type = listener_type_map.get(e.value)
        allowed_variants = VARIANT_MAP.get(selected_type, [])

        if allowed_variants:
            variant_select.options = allowed_variants
            variant_select.value = allowed_variants[0]
            variant_select.classes("hidden", remove=True)
        else:
            variant_select.options = []
            variant_select.value = None
            variant_select.classes("hidden", add=True)

    # --- UI: THE DIALOG (Rounded Corners) ---
    # Removed rounded-none (defaults to slight round) or use rounded
    with ui.dialog() as dialog, ui.card().classes(
        "tech-dialog w-[500px] p-0 rounded overflow-hidden"
    ):

        # Header
        with ui.row().classes(
            "w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"
        ):
            with ui.row().classes("gap-2 items-center"):
                ui.icon("terminal", color="emerald-500")
                ui.label("COMPILE_AGENT").classes(
                    "text-sm font-bold tracking-widest text-emerald-500 font-mono"
                )
            ui.button(icon="close", on_click=dialog.close).props(
                "dense flat size=sm color=grey"
            )

        # Body
        with ui.column().classes("p-6 gap-6 w-full"):

            # Name Input - Removed square
            name_input = (
                ui.input("IDENTITY", placeholder="agent_filename")
                .props("outlined dense dark color=emerald")
                .classes("w-full")
            )

            # Grid
            with ui.grid().classes("grid-cols-2 gap-4 w-full"):
                format_select = ui.select(
                    options=["exe", "dll", "ps1", "shellcode", "all"],
                    value="exe",
                    label="FORMAT",
                ).props("outlined dense dark color=emerald options-dense")

                listener_select = ui.select(
                    options=list(listener_type_map.keys()),
                    label="LISTENER",
                    on_change=_on_listener_change,
                ).props("outlined dense dark color=emerald options-dense")

            variant_select = (
                ui.select(label="VARIANT", options=[])
                .props("outlined dense dark color=emerald")
                .classes("w-full hidden")
            )

        # Footer
        with ui.row().classes(
            "w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"
        ):
            ui.button("ABORT", on_click=dialog.close).props(
                "flat dense color=grey no-caps"
            )

            # Action Button - Removed square
            build_btn = (
                ui.button("EXECUTE BUILD", on_click=_build_implant)
                .props("unelevated dense color=emerald text-color=white no-caps")
                .classes("font-bold tracking-wide")
            )

    dialog.open()
