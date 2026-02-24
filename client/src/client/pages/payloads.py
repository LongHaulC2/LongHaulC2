import structlog
from nicegui import ui

# --- Imports ---
from client.src.client.modules.api_calls import (
    build_implant,
    get_all_listener_data,
    get_build_status,
    get_payload_bytes,
    get_payload_data,
    get_payload_source_bytes,
)
from client.src.client.pages.footer import build_footer
from client.src.client.pages.menu import setup_menu

server_log = structlog.getLogger("server")


# ==============================================================================
#   UI HELPERS
# ==============================================================================
def stat_widget(label: str, value: str, icon: str, color: str = "emerald"):
    """Creates a small tech-styled stat card"""
    with ui.card().classes("flex-1 min-w-[150px] p-3 gap-1 bg-white/5 border border-white/10 rounded-sm no-shadow"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(label).classes("text-[10px] font-mono tracking-widest text-neutral-500 uppercase")
            ui.icon(icon, size="xs", color=f"{color}-500").classes("opacity-80")
        ui.label(str(value)).classes("text-xl font-bold font-mono tracking-wide text-neutral-200 truncate")


@ui.page("/payloads")
async def payloads():
    # Full Screen Layout Setup
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    # Inject CSS & Menu
    setup_menu("Payloads")

    await payloads_view()
    await build_footer()


async def payloads_view():
    # --- MAIN GLASS PANEL ---
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        # --- HEADER BAR ---
        with ui.row().classes("w-full items-center justify-between tech-header-bar"):
            # Left: Identity
            with ui.row().classes("items-center gap-3"):
                ui.icon("layers", color="emerald-500").classes("text-xl")
                ui.label("PAYLOAD_LIBRARY //").classes("tech-label-title")

            # Right: Controls
            with ui.row().classes("items-center gap-2"):
                with (
                    ui.button(on_click=start_payload_dialogue)
                    .classes("tech-btn-action px-4")
                    .props("flat no-caps dense")
                ):
                    ui.icon("add_circle", size="xs").classes("mr-2")
                    ui.label("COMPILE NEW").classes("text-xs font-bold tracking-wide")

                ui.button(icon="refresh", on_click=lambda: ui.navigate.to("/payloads")).props(
                    "dense flat size=sm"
                ).classes("tech-btn-ghost")

        # --- CONTENT AREA ---
        with ui.column().classes("w-full flex-grow p-6 gap-6 overflow-hidden"):
            # Fetch Data
            payload_data_response = await get_payload_data()
            payload_data = payload_data_response.get("data", [])

            # --- 1. ARSENAL STATS ROW ---
            # Calculate metrics client-side
            total_count = len(payload_data)
            listeners = set(p.get("payload_listener_uuid") for p in payload_data)
            last_built = payload_data[-1].get("payload_name") if payload_data else "N/A"

            with ui.row().classes("w-full gap-4"):
                stat_widget("TOTAL ARTIFACTS", str(total_count), "storage", "emerald")
                stat_widget("ACTIVE LISTENERS", str(len(listeners)), "hub", "blue")
                stat_widget("LATEST BUILD", last_built, "history", "purple")

            # --- 2. MAIN TABLE AREA ---
            with ui.card().classes(
                "w-full flex-grow bg-white/5 border border-white/5 p-0 rounded overflow-hidden flex flex-col"
            ):
                if not payload_data:
                    with ui.column().classes("w-full h-full items-center justify-center opacity-30"):
                        ui.icon("inbox", size="4em")
                        ui.label("NO ARTIFACTS FOUND").classes("font-mono text-sm mt-2")
                else:
                    await render_payloads(payload_data=payload_data)


async def render_payloads(payload_data: dict):
    """Renders the list of payloads in a dashboard table"""

    # Fetch Listener Data for Lookup
    all_listeners_resp = await get_all_listener_data()
    all_listeners = all_listeners_resp.get("data", [])
    listener_map = {
        listener.get("listener_uuid"): listener.get("listener_name", "Unknown") for listener in all_listeners
    }

    # Helper to guess format for badge styling
    def get_fmt(name):
        if name.endswith(".exe"):
            return "EXE"
        if name.endswith(".dll"):
            return "DLL"
        if name.endswith(".bin"):
            return "BIN"
        if name.endswith(".ps1"):
            return "PS1"
        return "RAW"

    # Prepare Rows
    table_rows = []
    for p in payload_data:
        l_uuid = p.get("payload_listener_uuid", "Unknown")
        p_name = p.get("payload_name", "Unnamed")

        table_rows.append(
            {
                "id": p.get("id"),
                "name": p_name,
                "fmt": get_fmt(p_name),
                "hash": p.get("payload_hash", ""),
                "listener": listener_map.get(l_uuid, "Unknown"),
                "uuid": l_uuid,
            }
        )

    # Action Handlers
    async def handle_download(e):
        row = e.args
        ui.notify(f"Retrieving {row['name']}...", type="info", color="grey-9")
        await download_payload(hash=row["hash"], name=row["name"])

    async def handle_source_download(e):
        row = e.args
        ui.notify(f"Retrieving {row['name']}...", type="info", color="grey-9")
        await download_payload_source(hash=row["hash"], name=row["name"])

    # Search Bar Logic
    filter_text = (
        ui.input(placeholder="SEARCH ARTIFACTS...")
        .props("outlined dense dark color=emerald input-class=text-xs")
        .classes("m-3 w-96")
    )

    # Define Columns
    columns = [
        {
            "name": "name",
            "label": "IDENTITY",
            "field": "name",
            "align": "left",
            "sortable": True,
        },
        {
            "name": "fmt",
            "label": "FORMAT",
            "field": "fmt",
            "align": "left",
            "sortable": True,
        },
        {
            "name": "listener",
            "label": "LINKED LISTENER",
            "field": "listener",
            "align": "left",
            "sortable": True,
        },
        {
            "name": "hash",
            "label": "HASH (MD5)",
            "field": "hash",
            "align": "left",
            "classes": "font-mono text-[10px] opacity-50 tracking-tighter",
        },
        {"name": "actions", "label": "Downloads", "field": "actions", "align": "right"},
    ]

    # Render Table
    table = (
        ui.table(columns=columns, rows=table_rows, row_key="id", pagination=10)
        .classes("w-full bg-transparent no-shadow text-neutral-300 flex-grow")
        .bind_filter_from(filter_text, "value")
    )

    # --- CUSTOM SLOTS ---

    # Header Styling
    table.add_slot(
        "header",
        r"""
        <q-tr
            :props="props"
            class="bg-black/20 text-neutral-500 uppercase text-[10px]
                font-bold tracking-widest border-b border-white/10"
        >
            <q-th v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.label }}
            </q-th>
        </q-tr>
        """,
    )

    # Format Badge Slot
    table.add_slot(
        "body-cell-fmt",
        r"""
        <q-td :props="props">
            <q-badge :color="props.value === 'EXE' ? 'blue-9' : props.value === 'DLL' ? 'purple-9' : 'grey-8'"
                     text-color="white" :label="props.value" class="font-mono text-[10px] px-2 py-0.5 rounded-sm" />
        </q-td>
    """,
    )

    # Listener Slot
    table.add_slot(
        "body-cell-listener",
        r"""
        <q-td :props="props">
            <div class="row items-center gap-2">
                <q-icon name="hub" size="xs" class="text-emerald-600" />
                <span class="text-xs font-mono">{{ props.value }}</span>
            </div>
        </q-td>
    """,
    )

    # Action Buttons Slot
    table.add_slot(
        "body-cell-actions",
        r"""
        <q-td :props="props">
            <div class="row items-center justify-end no-wrap gap-1">
                <q-btn icon="download" flat dense size="sm" color="grey-5"
                    class="hover:text-emerald-400 transition-colors"
                    @click="$parent.$emit('download', props.row)">
                    <q-tooltip class="bg-neutral-900 text-xs">BINARY</q-tooltip>
                </q-btn>
                <q-btn icon="code" flat dense size="sm" color="grey-5"
                    class="hover:text-emerald-400 transition-colors"
                    @click="$parent.$emit('source_download', props.row)">
                    <q-tooltip class="bg-neutral-900 text-xs">SOURCE</q-tooltip>
                </q-btn>
            </div>
        </q-td>
        """,
    )

    # Register Listeners
    table.on("download", handle_download)
    table.on("source_download", handle_source_download)


# ==============================================================================
#   DIALOG & BUILD LOGIC
# ==============================================================================
async def start_payload_dialogue():
    """Opens the Build Dialog"""

    # --- 1. Fetch Data ---
    response = await get_all_listener_data()
    listeners_list = response.get("data", [])

    # Map Name -> UUID
    listener_uuid_map = {listener["listener_name"]: listener["listener_uuid"] for listener in listeners_list}

    # --- 2. Event Handlers ---

    def _on_listener_change(e):
        """
        Updates GET/POST options to match the selected listeners list.
        """
        selected_names = e.value or []

        # --- Update GET Dropdown ---
        profile_get_select.options = selected_names

        if selected_names:
            profile_get_select.enable()
            if not profile_get_select.value or profile_get_select.value not in selected_names:
                profile_get_select.value = selected_names[0]
        else:
            profile_get_select.value = None
            profile_get_select.disable()

        # --- Update POST Dropdown ---
        profile_post_select.options = selected_names

        if selected_names:
            profile_post_select.enable()
            if not profile_post_select.value or profile_post_select.value not in selected_names:
                profile_post_select.value = selected_names[0]
        else:
            profile_post_select.value = None
            profile_post_select.disable()

        # Force UI refresh
        profile_get_select.update()
        profile_post_select.update()

    async def _build_implant():
        if not all(
            [
                name_input.value,
                listener_select.value,
                format_select.value,
                profile_get_select.value,
                profile_post_select.value,
            ]
        ):
            ui.notify("MISSING REQUIRED FIELDS", type="warning", color="orange-9")
            return

        progress_bar.classes(remove="opacity-0")
        build_btn.props("loading")
        progress_bar.set_value(0.25)

        # Build Data
        # listener_dict = {}
        # for lst_name in listener_select.value:
        #     uuid = listener_uuid_map.get(lst_name)
        #     if uuid:
        #         listener_dict[uuid] = {}  # {
        #         #     "profile_get": profile_get_select.value,
        #         #     "profile_post": profile_post_select.value,
        #         # }

        # list of listener UUID's to include in payload
        listener_uuids = []
        for lst_name in listener_select.value:
            uuid = listener_uuid_map.get(lst_name)
            if uuid:
                listener_uuids.append(uuid)

        # API Call
        result = await build_implant(
            implant_name=name_input.value,
            listener_uuids=listener_uuids,
            output_format=format_select.value,
            initial_get_profile_listener_uuid=listener_uuid_map.get(profile_get_select.value),
            initial_post_profile_listener_uuid=listener_uuid_map.get(profile_post_select.value),
        )

        # Build Status Polling Logic
        build_uuid = result.get("data", {}).get("build_uuid")
        if build_uuid:
            progress_bar.set_value(0.75)

        build_btn.props("loading=false")

        async def poll_build_status():
            result = await get_build_status(build_uuid)
            status = result.get("data", {}).get("build_status")

            if status == "complete":
                payload_hash = result.get("data", {}).get("payload_hash")
                payload_name = result.get("data", {}).get("payload_name")

                progress_bar.set_value(1)
                progress_bar.props("color=emerald-4")
                build_btn.props("loading=false")

                download_payload_button.enable()
                download_payload_button.on_click(lambda: download_payload(hash=payload_hash, name=payload_name))

                download_payload_source_button.enable()
                download_payload_source_button.on_click(
                    lambda: download_payload_source(hash=payload_hash, name=payload_name)
                )

                status_timer.deactivate()

            elif status == "failed":
                progress_bar.classes("opacity-0")
                progress_bar_fail.classes(remove="opacity-0")
                progress_bar_fail.set_value(1)

                ui.notify("BUILD FAILED", type="negative")
                build_btn.props("loading=false")
                status_timer.deactivate()

        status_timer = ui.timer(1.0, poll_build_status, active=True)

    # --- 3. UI Layout ---
    with ui.dialog() as dialog, ui.card().classes("tech-dialog w-[600px] p-0 rounded overflow-hidden"):
        # Header
        with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
            with ui.row().classes("gap-2 items-center"):
                ui.icon("terminal", color="emerald-500")
                ui.label("COMPILE_ARTIFACT").classes("text-sm font-bold tracking-widest text-emerald-500 font-mono")
            ui.button(icon="close", on_click=dialog.close).props("dense flat size=sm color=grey")

        # Body
        with ui.column().classes("p-6 gap-5 w-full"):
            # IDENTITY & FORMAT
            with ui.row().classes("w-full gap-4"):
                name_input = (
                    ui.input("IDENTITY", placeholder="filename (no ext)")
                    .props("outlined dense dark color=emerald")
                    .classes("flex-grow")
                )

                format_select = (
                    ui.select(
                        options=["exe", "dll", "ps1", "shellcode", "all"],
                        value="exe",
                        label="FORMAT",
                    )
                    .props("outlined dense dark color=emerald options-dense")
                    .classes("w-1/3")
                )

            # LISTENER SELECTION
            listener_select = (
                ui.select(
                    options=list(listener_uuid_map.keys()),
                    label="Implant Profiles",
                    multiple=True,
                    on_change=_on_listener_change,
                )
                .props("outlined dense dark color=emerald options-dense use-chips stack-label")
                .classes("w-full")
            )
            with listener_select:
                ui.tooltip("The profiles to include in the payload").classes("bg-green-700")

            # PROFILE CONFIG
            with ui.row().classes("w-full"):  # bg-white/5 rounded border border-white/5
                profile_get_select = (
                    ui.select(label="Initial Get Profile", options=[])
                    .props("outlined dense dark color=emerald options-dense")
                    .classes("flex-1")
                )
                profile_get_select.disable()

                profile_post_select = (
                    ui.select(label="Initial Post Profile", options=[])
                    .props("outlined dense dark color=emerald options-dense")
                    .classes("flex-1")
                )
                profile_post_select.disable()

                with profile_get_select:
                    ui.tooltip("The profile to use for the initial GET requests").classes("bg-green-700")
                with profile_post_select:
                    ui.tooltip("The profile to use for the initial POST requests").classes("bg-green-700")

        # Footer
        with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3 relative"):
            # Progress Bars
            progress_bar = (
                ui.linear_progress(value=0, show_value=False, color="emerald-400")
                .props("instant-feedback track-color=transparent")
                .classes("absolute top-0 left-0 w-full h-[2px] opacity-0 transition-opacity")
            )

            progress_bar_fail = (
                ui.linear_progress(value=0, show_value=False, color="red-500")
                .props("instant-feedback track-color=transparent")
                .classes("absolute top-0 left-0 w-full h-[2px] opacity-0 transition-opacity")
            )

            # Buttons
            download_payload_button = (
                ui.button("BINARY", icon="download")
                .props("unelevated dense color=emerald text-color=white no-caps")
                .classes("font-bold tracking-wide disabled:opacity-50")
            )
            download_payload_button.disable()

            download_payload_source_button = (
                ui.button("SOURCE", icon="code")
                .props("unelevated dense color=emerald text-color=white no-caps")
                .classes("font-bold tracking-wide disabled:opacity-50")
            )
            download_payload_source_button.disable()

            ui.separator().classes("vertical mx-2 bg-white/10")

            build_btn = (
                ui.button("COMPILE", on_click=_build_implant)
                .props("unelevated dense color=emerald text-color=white no-caps")
                .classes("font-bold tracking-wide")
            )

    dialog.open()


async def download_payload(hash, name):
    file_bytes = await get_payload_bytes(hash)
    if file_bytes:
        ui.download(file_bytes, filename=f"{name}.bin")
        ui.notify("Transfer Complete", type="positive")
    else:
        ui.notify("Transfer Failed", type="negative")


async def download_payload_source(hash, name):
    file_bytes = await get_payload_source_bytes(hash)
    if file_bytes:
        ui.download(file_bytes, filename=f"{name}_source.zip")
        ui.notify("Transfer Complete", type="positive")
    else:
        ui.notify("Transfer Failed", type="negative")
