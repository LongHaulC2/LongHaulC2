import structlog
from nicegui import ui

# Imports
from client.src.client.modules.api_calls import (
    build_implant,
    get_all_listener_data,
    get_build_status,
    get_payload_bytes,
    get_payload_data,
    get_payload_source_bytes,
)
from client.src.client.pages.footer import build_footer
from client.src.client.pages.formatted_tooltip import formatted_tooltip
from client.src.client.pages.menu import setup_menu

server_log = structlog.getLogger("server")
payload_stats = {"total": "0", "active_listeners": "0", "latest": "N/A"}


def stat_widget(label: str, icon: str, color: str, key: str):
    """Compact telemetry widget for the sub-header bar"""
    with ui.element("div").classes("flex-1 h-full px-4 gap-2 flex items-center border-r border-white/5 bg-white/2"):
        ui.icon(icon, size="14px", color=f"{color}-500").classes("opacity-70")
        ui.label(label).classes("tech-label-sub")
        # .classes("text-[10px] font-mono tracking-tighter text-neutral-500 uppercase")
        ui.label().bind_text_from(payload_stats, key).classes("tech-label-sub")


@ui.page("/payloads")
async def payloads():
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    setup_menu("Payloads")
    await payloads_view()
    await build_footer()


async def payloads_view():
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        # HEADER
        with ui.row().classes("w-full items-center justify-between tech-header-bar"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("layers", color="emerald-500").classes("text-xl")
                ui.label("PAYLOAD_LIBRARY //").classes("tech-label-header-section")

            with ui.row().classes("items-center gap-2"):
                with (
                    ui.button(on_click=start_payload_dialogue)
                    .classes("tech-btn-action px-2")
                    .props("dense flat size=sm")
                ):
                    ui.icon("add", size="xs").classes("mr-1")
                    ui.label("PAYLOAD").classes("tech-label-sub")
                    # ui.tooltip("Build New Payload")
                    formatted_tooltip(title="Build a new payload")
                ui.button(icon="refresh", on_click=lambda: ui.navigate.to("/payloads")).props(
                    "dense flat size=sm"
                ).classes("tech-btn-action-2")

        # SUB-HEADER TELEMETRY (High & Tight)
        with ui.row().classes("w-full h-8 gap-0 bg-[#0c0c0c] border-b border-white/5 items-center"):
            stat_widget("Total Artifacts:", "storage", "emerald", "total")
            stat_widget("Active Listeners:", "hub", "blue", "active_listeners")
            stat_widget("Latest Build:", "history", "purple", "latest")

        # CONTENT
        with ui.column().classes("w-full p-0 flex-grow overflow-hidden"):
            await render_payloads_table()


async def render_payloads_table():
    # Header Search Strip
    with ui.row().classes("w-full items-center px-2 py-1 bg-white/2"):
        filter_text = (
            ui.input(placeholder="FILTER ARTIFACTS...")
            .props("outlined dense dark color=emerald input-class=text-[10px] autofocus")
            .classes("w-64 tech-input")
        )

    # Column Mapping
    columns = [
        {"name": "name", "label": "Payload Name", "field": "name", "align": "left", "sortable": True},
        {"name": "fmt", "label": "FORMAT", "field": "fmt", "align": "left", "sortable": True},
        {"name": "listener", "label": "LINKED LISTENER(s)", "field": "listener", "align": "left", "sortable": True},
        {"name": "hash", "label": "HASH (MD5)", "field": "hash", "align": "left"},
        {"name": "actions", "label": "DOWNLOAD", "field": "actions", "align": "right"},
    ]

    table = (
        ui.table(columns=columns, rows=[], row_key="id", pagination=15)
        .classes("w-full flex-grow tech-table-base tech-table-head tech-table-body tech-table-row-hover")
        .bind_filter_from(filter_text, "value")
    )

    def get_fmt(name):
        ext = name.split(".")[-1].upper() if "." in name else "RAW"
        return ext[:3]

    async def refresh_data():
        p_resp = await get_payload_data()
        payloads = (p_resp or {}).get("data", [])

        l_resp = await get_all_listener_data()
        l_map = {
            _listener.get("listener_uuid"): _listener.get("listener_name", "Unknown")
            for _listener in (l_resp or {}).get("data", [])
        }

        rows = []
        listeners_seen = set()
        for p in payloads:
            l_uuid = p.get("payload_listener_uuid")
            listeners_seen.add(l_uuid)
            rows.append(
                {
                    "id": p.get("id"),
                    "name": p.get("payload_name", "Unnamed"),
                    "fmt": get_fmt(p.get("payload_name", "")),
                    "hash": p.get("payload_hash", ""),
                    "listener": l_map.get(l_uuid, "Unknown"),
                }
            )

        table.rows = rows
        payload_stats.update(
            {
                "total": str(len(rows)),
                "active_listeners": str(len(listeners_seen)),
                "latest": rows[-1]["name"] if rows else "N/A",
            }
        )

    await refresh_data()

    # Table Slots
    table.add_slot(
        "header",
        r"""
        <q-tr :props="props" class="bg-black/40 text-neutral-500 uppercase text-[10px] font-bold tracking-widest">
            <q-th v-for="col in props.cols" :key="col.name" :props="props">{{ col.label }}</q-th>
        </q-tr>
    """,
    )

    table.add_slot(
        "body-cell-fmt",
        r"""
        <q-td :props="props">
            <q-badge :color="props.value === 'EXE' ? 'blue-10' : props.value === 'DLL' ? 'purple-10' : 'grey-9'"
                     class="font-mono text-[9px] px-1.5 rounded-sm">{{ props.value }}</q-badge>
        </q-td>
    """,
    )

    table.add_slot(
        "body-cell-hash",
        r"""
        <q-td :props="props">
            <span class="font-mono text-[12px] opacity-40 hover:opacity-100 cursor-pointer">{{ props.value }}</span>
        </q-td>
    """,
    )

    table.add_slot(
        "body-cell-actions",
        r"""
        <q-td :props="props">
            <div class="row items-center justify-end gap-1 no-wrap">
                <q-btn icon="download" flat dense size="sm" color="grey-6" @click="$parent.$emit('bin', props.row)">
                    <q-tooltip class="bg-black">BINARY</q-tooltip>
                </q-btn>
                <q-btn icon="code" flat dense size="sm" color="grey-6" @click="$parent.$emit('src', props.row)">
                    <q-tooltip class="bg-black">SOURCE</q-tooltip>
                </q-btn>
            </div>
        </q-td>
    """,
    )

    table.on("bin", lambda e: download_payload(hash=e.args["hash"], name=e.args["name"]))
    table.on("src", lambda e: download_payload_source(hash=e.args["hash"], name=e.args["name"]))


# ====================
#   DIALOG & BUILD LOGIC
# ====================
async def start_payload_dialogue():
    """Opens the Build Dialog"""

    # 1. Fetch Data
    response = await get_all_listener_data()
    listeners_list = response.get("data", [])

    # Map Name -> UUID
    listener_uuid_map = {listener["listener_name"]: listener["listener_uuid"] for listener in listeners_list}

    # 2. Event Handlers

    def _on_listener_change(e):
        """
        Updates GET/POST options to match the selected listeners list.
        """
        selected_names = e.value or []

        # Update GET Dropdown
        profile_get_select.options = selected_names

        if selected_names:
            profile_get_select.enable()
            if not profile_get_select.value or profile_get_select.value not in selected_names:
                profile_get_select.value = selected_names[0]
        else:
            profile_get_select.value = None
            profile_get_select.disable()

        # Update POST Dropdown
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

        # put together options dict:
        debug_value = debug_logs_toggle.value
        clear_cache_value = clear_cache_toggle.value
        options = {"debug": debug_value, "clear_cache": clear_cache_value}

        # API Call
        result = await build_implant(
            implant_name=name_input.value,
            listener_uuids=listener_uuids,
            output_format=format_select.value,
            initial_get_profile_listener_uuid=listener_uuid_map.get(profile_get_select.value),
            initial_post_profile_listener_uuid=listener_uuid_map.get(profile_post_select.value),
            options=options,
        )

        # Build Status Polling Logic
        build_uuid = result.get("data", {}).get("build_uuid")
        if build_uuid:
            progress_bar.set_value(0.75)

        # ! build_time is a float
        build_time = result.get("data", {}).get("build_stats", {}).get("build_time", 0.0)
        if build_time:
            # ui.label(f"Build Time: {build_time}")
            build_time = round(build_time, 2)
            # ! Again, because build_time is a float, cast to a STR
            build_time_value.set_text(str(build_time))

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

    # 3. UI Layout
    with ui.dialog() as dialog, ui.card().classes("tech-dialog w-[600px] p-0 rounded overflow-hidden"):
        # Header
        with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
            with ui.row().classes("gap-2 items-center"):
                ui.icon("layers", color="emerald-500")
                ui.label("NEW PAYLOAD").classes("tech-label-sub")
            ui.button(icon="close", on_click=dialog.close).props("dense flat size=sm color=grey")

        # Body
        with ui.column().classes("p-6 gap-5 w-full"):
            # IDENTITY & FORMAT
            with ui.row().classes("w-full gap-4"):
                name_input = (
                    ui.input("Payload Name", placeholder="filename (no ext)")
                    .props("outlined dense dark color=emerald")
                    .classes("flex-grow tech-input")
                )
                with name_input:
                    formatted_tooltip(
                        title="Name for the payload",
                        body="All generated payloads will have this name, and the appropriate extension added to it.",
                    )

                format_select = (
                    ui.select(
                        options=["exe", "dll", "ps1", "shellcode", "all"],
                        value="exe",
                        label="FORMAT",
                    )
                    .props("outlined dense dark color=emerald options-dense")
                    .classes("w-1/3 tech-select")
                )
                with format_select:
                    formatted_tooltip(
                        title="[Not Implemented] The format of the implant output",
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
                .classes("w-full tech-select")
            )
            with listener_select:
                # ui.tooltip("The profiles to include in the payload").classes("bg-green-700")
                formatted_tooltip(
                    title="Profile to include in the payload",
                    body="These are compiled in, and can be switched with the `strat` command.",
                )

            # PROFILE CONFIG
            with ui.row().classes("w-full"):  # bg-white/5 rounded border border-white/5
                profile_get_select = (
                    ui.select(label="Initial Get Profile", options=[])
                    .props("outlined dense dark color=emerald options-dense")
                    .classes("flex-1 tech-select")
                )
                profile_get_select.disable()

                profile_post_select = (
                    ui.select(label="Initial Post Profile", options=[])
                    .props("outlined dense dark color=emerald options-dense")
                    .classes("flex-1 tech-select")
                )
                profile_post_select.disable()

                with profile_get_select:
                    formatted_tooltip("The profile to use for the initial GET requests")
                with profile_post_select:
                    formatted_tooltip("The profile to use for the initial POST requests")

            ui.separator()
            with ui.expansion("Additional Options").classes("tech-expansion w-full"):  # noqa - niecgui styling
                # Container for the list. Removed the top border since the expansion handles it now.
                with ui.column().classes("w-full p-0 gap-0"):
                    # sep at start
                    ui.separator()

                    # Debug logs options
                    with ui.row().classes("w-full items-center justify-between p-3 border-b border-white/5"):
                        ui.label("IMPLANT DEBUG LOGS").classes(
                            "text-[11px] text-zinc-400 font-bold tracking-widest font-mono uppercase"
                        )
                        debug_logs_toggle = (
                            ui.toggle({False: "DISABLED", True: "ENABLED"}, value=False)
                            .classes("tech-toggle")
                            .props("dark color=emerald")
                        )
                        with debug_logs_toggle:
                            # ui.tooltip("Enable output to terminal via the implant").classes(
                            #     "bg-neutral-900 border border-emerald-500/30 font-mono text-xs"
                            # )
                            formatted_tooltip(
                                title="Enable Debug Logs",
                                body="Enables debug logs for the implant. These print to STDOUT, "
                                "and to a file named `implant_debug.log`",
                            )

                    # Build Cache option
                    with ui.row().classes("w-full items-center justify-between p-3"):
                        ui.label("BUILD CACHE").classes(
                            "text-[11px] text-zinc-400 font-bold tracking-widest font-mono uppercase"
                        )
                        clear_cache_toggle = (  # noqa - will use eventually
                            ui.toggle({False: "KEEP", True: "CLEAR"}, value=False)
                            .classes("tech-toggle")
                            .props("dark color=emerald")
                        )
                        with clear_cache_toggle:
                            formatted_tooltip(
                                title="Clear Build Cache",
                                body="Clears the build cache of the implant. Useful if editing the implant code",
                                footer="<i>Expect compile times to be slightly longer<i>",
                            )

                    # sep at end
                    ui.separator()

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

            # split these into a row, so they have their own sides & don't clash
            with ui.row().classes("w-full items-center"):
                # Left side: build time
                ui.label("Build Time [seconds]: ").classes("text-gray-600 tech-label-sub")
                build_time_value = ui.label().classes("text-gray-600 tech-label-sub")

                # Spacer pushes everything after it to the right
                ui.space()

                # Right side: buttons
                download_payload_button = (
                    ui.button("BINARY", icon="download")
                    .props("dense flat size=sm")
                    .classes("font-bold tracking-wide disabled:opacity-50 tech-btn-action-2")
                )
                download_payload_button.disable()

                download_payload_source_button = (
                    ui.button("SOURCE", icon="code")
                    .props("dense flat size=sm")
                    .classes("font-bold tracking-wide disabled:opacity-50 tech-btn-action-2")
                )
                download_payload_source_button.disable()

            ui.separator().classes("vertical mx-2 bg-white/10")

            build_btn = (
                ui.button("BUILD", on_click=_build_implant, icon="add")
                .props("dense flat size=sm")
                .classes("font-bold tracking-wide tech-btn-action")
            )

    dialog.open()


async def download_payload(hash, name):
    file_bytes = await get_payload_bytes(hash)
    if file_bytes:
        ui.download(file_bytes, filename=f"{name}")
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
