import logging
from itertools import groupby

from nicegui import ui

# --- Imports ---
from client.src.client.modules.api_calls import (
    build_implant,
    get_all_listener_data,
    get_listener_data,
    get_payload_bytes,
    get_payload_data,
    get_payload_source_bytes,
)
from client.src.client.pages.menu import setup_menu

server_log = logging.getLogger("server")


@ui.page("/payloads")
async def payloads():
    # 1. Full Screen Layout Setup
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    # 2. Inject CSS & Menu
    setup_menu("Payloads")

    await payloads_view()


async def payloads_view():

    # --- MAIN GLASS PANEL ---
    # Using 'tech-glass-panel' from CSS to handle the visuals
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):

        # --- HEADER BAR ---
        # Using 'tech-header-bar' from CSS
        with ui.row().classes("w-full items-center justify-between tech-header-bar"):

            # Left: Identity
            with ui.row().classes("items-center gap-3"):
                ui.icon("layers", color="emerald-500").classes("text-xl")
                ui.label("PAYLOAD_LIBRARY //").classes("tech-label-title")

            # Right: Controls
            with ui.row().classes("items-center gap-2"):
                # "Compile New" Button
                with ui.button(on_click=start_payload_dialogue).classes(
                    "tech-btn-action px-4"
                ).props("flat no-caps dense"):
                    ui.icon("add_circle", size="xs").classes("mr-2")
                    ui.label("COMPILE NEW").classes("text-xs font-bold tracking-wide")

                # Refresh Button
                ui.button(icon="refresh", on_click=lambda: ui.open("/payloads")).props(
                    "dense flat size=sm"
                ).classes("tech-btn-ghost")

        # --- CONTENT AREA ---
        with ui.scroll_area().classes("w-full flex-grow p-6 tech-scroll"):

            payload_data_response = await get_payload_data()
            payload_data = payload_data_response.get("data", [])

            if not payload_data:
                # Empty State
                with ui.column().classes(
                    "w-full h-64 items-center justify-center opacity-30"
                ):
                    ui.icon("inbox", size="4em")
                    ui.label("NO ARTIFACTS FOUND").classes("font-mono text-sm mt-2")
            else:
                await render_payloads(payload_data=payload_data)


async def render_payloads(payload_data: dict):
    """Renders the list of payloads using the Tech Expansion component"""

    # 1. Define Columns
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

    # Get all lsiteenrs at once, create a lookup dictionary: { 'uuid_string': 'Listener Name', ... }
    all_listeners_resp = await get_all_listener_data()
    all_listeners = all_listeners_resp.get("data", [])
    # Map UUID -> Name for O(1) lookup inside the loop
    listener_map = {
        l.get("listener_uuid"): l.get("listener_name", "Unknown") for l in all_listeners
    }

    # 2. Group Data by Listener
    sorted_data = sorted(
        payload_data, key=lambda x: x.get("payload_listener_uuid", "Unknown")
    )
    grouped_payloads = {
        k: list(v)
        for k, v in groupby(
            sorted_data, key=lambda x: x.get("payload_listener_uuid", "Unknown")
        )
    }

    # 3. Action Handlers
    async def handle_download(e):
        row = e.args
        ui.notify(f"Retrieving {row['name']}...", type="info", color="grey-9")
        file_bytes = await get_payload_bytes(row["hash"])
        if file_bytes:
            ui.download(file_bytes, filename=f'{row["name"]}.bin')
            ui.notify("Transfer Complete", type="positive")
        else:
            ui.notify("Transfer Failed", type="negative")

    async def handle_source_download(e):
        row = e.args
        ui.notify(f"Retrieving {row['name']}...", type="info", color="grey-9")
        file_bytes = await get_payload_source_bytes(row["hash"])
        if file_bytes:
            ui.download(file_bytes, filename=f"{row["name"]}_source.zip")
            ui.notify("Transfer Complete", type="positive")
        else:
            ui.notify("Transfer Failed", type="negative")

    # 4. Render Groups
    listener_data = (await get_all_listener_data()).get("data")
    for listener_uuid, payloads in grouped_payloads.items():
        # Prepare Rows
        table_rows = [
            {
                "id": p.get("id"),
                "name": p.get("payload_name", "Unnamed"),
                "hash": p.get("payload_hash", ""),
                "uuid": listener_uuid,
            }
            for p in payloads
        ]

        # Fetch Context
        # listener_data = await get_listener_data(listener_uuid)
        listener_name = listener_map.get(listener_uuid, "Unknown")

        # --- TECH EXPANSION COMPONENT ---
        # "tech-expansion" class handles all the border/background logic in CSS
        with ui.expansion().classes("w-full tech-expansion group") as expansion:

            # Header Slot
            with expansion.add_slot("header"):
                with ui.row().classes("w-full items-center py-2 px-1"):
                    ui.icon("dns", size="sm").classes(
                        "mr-4 text-neutral-600 group-hover:text-emerald-400 transition-colors"
                    )

                    with ui.column().classes("gap-0"):
                        ui.label(listener_name).classes(
                            "text-sm font-bold text-neutral-200 tracking-wide uppercase"
                        )
                        ui.label(f"UUID: {listener_uuid}").classes(
                            "tech-label-subtitle"
                        )

                    ui.space()

                    # Badge
                    with ui.row().classes("items-center gap-2"):
                        ui.label(f"{len(table_rows)} ITEMS").classes(
                            "text-[10px] font-bold text-neutral-600 bg-black/20 px-2 py-1 rounded-sm"
                        )

            # Table ("tech-table-flush" handles zero-margin logic)
            table = ui.table(columns=columns, rows=table_rows, row_key="id").classes(
                "tech-table-flush"
            )

            # Inject Download Buttons
            table.add_slot(
                "body-cell-actions",
                r"""
                <q-td :props="props">
                    <div class="row items-center justify-end no-wrap gap-1">
                        
                        <q-btn icon="download" flat dense size="sm" color="grey-5" 
                            class="hover:text-emerald-400 transition-colors"
                            @click="$parent.$emit('download', props.row)">
                            <q-tooltip class="bg-neutral-900 text-xs">DOWNLOAD BINARY</q-tooltip>
                        </q-btn>

                        <q-btn icon="code" flat dense size="sm" color="grey-5" 
                            class="hover:text-emerald-400 transition-colors"
                            @click="$parent.$emit('source_download', props.row)">
                            <q-tooltip class="bg-neutral-900 text-xs">DOWNLOAD SOURCE</q-tooltip>
                        </q-btn>

                    </div>
                </q-td>
                """,
            )

            # Register Listeners for both events
            table.on("download", handle_download)

            # Make sure you have this function defined above!
            table.on("source_download", handle_source_download)


async def start_payload_dialogue():
    """Opens the Build Dialog"""

    # --- Data Setup ---
    VARIANT_MAP = {"http": ["http_wininet"]}
    response = await get_all_listener_data()
    listeners_list = response.get("data", [])
    listener_type_map = {l["listener_name"]: l["listener_type"] for l in listeners_list}
    listener_uuid_map = {l["listener_name"]: l["listener_uuid"] for l in listeners_list}

    # --- Logic ---
    async def _build_implant():
        name = name_input.value
        listener_name = listener_select.value
        variant = variant_select.value
        fmt = format_select.value

        if not all([name, listener_name, fmt]):
            ui.notify("MISSING REQUIRED FIELDS", type="warning", color="orange-9")
            return

        build_btn.props("loading")

        result = await build_implant(
            implant_name=name,
            implant_listener_uuid=listener_uuid_map.get(listener_name),
            implant_variant=variant if variant_select.visible else None,
            output_format=fmt,
        )

        build_btn.props("loading=false")

        if result:
            ui.notify(
                f"BUILD STARTED: {name}.{fmt}", type="positive", color="emerald-9"
            )
            dialog.close()
        else:
            ui.notify("COMPILATION FAILED", type="negative")

    def _on_listener_change(e):
        allowed = VARIANT_MAP.get(listener_type_map.get(e.value), [])
        variant_select.options = allowed
        variant_select.value = allowed[0] if allowed else None
        variant_select.classes("hidden", remove=bool(allowed), add=not bool(allowed))

    # --- UI ---
    # "tech-dialog" handles the dark theme and borders
    with ui.dialog() as dialog, ui.card().classes(
        "tech-dialog w-[500px] p-0 rounded overflow-hidden"
    ):

        # Dialog Header
        with ui.row().classes(
            "w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"
        ):
            with ui.row().classes("gap-2 items-center"):
                ui.icon("terminal", color="emerald-500")
                ui.label("BUILD_IMPLANT_PAYLOAD").classes(
                    "text-sm font-bold tracking-widest text-emerald-500 font-mono"
                )
            ui.button(icon="close", on_click=dialog.close).props(
                "dense flat size=sm color=grey"
            )

        # Dialog Body
        with ui.column().classes("p-6 gap-6 w-full"):
            name_input = (
                ui.input("IDENTITY", placeholder="agent_filename")
                .props("outlined dense dark color=emerald")
                .classes("w-full")
            )

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

        # Dialog Footer
        with ui.row().classes(
            "w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"
        ):
            ui.button("ABORT", on_click=dialog.close).props(
                "flat dense color=grey no-caps"
            )

            build_btn = (
                ui.button("EXECUTE BUILD", on_click=_build_implant)
                .props("unelevated dense color=emerald text-color=white no-caps")
                .classes("font-bold tracking-wide")
            )

    dialog.open()
