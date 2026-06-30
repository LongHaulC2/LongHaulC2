import structlog
from nicegui import app, ui

# Imports
from client.modules.api_calls import (
    delete_listener,
    get_all_listener_data,
    get_all_profiles,
    get_profile_by_name,
    restart_listener,
    start_listener,
    start_listener_from_existing,
    stop_listener,
    upload_profile,
)
from client.modules.navigate_hook import get_current_uri, navigate
from client.pages.footer import build_footer
from client.pages.formatted_tooltip import formatted_tooltip
from client.pages.menu import setup_menu
from client.utils.helpers import notify

stats = {"total": 0, "online": 0}

server_log = structlog.getLogger("server")
server_log.info("Loading /listeners page")


# ====================
#   UI HELPERS
# ====================


def stat_widget(label: str, icon: str, color: str, key: str):
    with ui.element("div").classes("flex-1 h-full px-4 gap-2 flex items-center border-r border-white/5 bg-white/2"):
        ui.icon(icon, size="14px", color=f"{color}-500").classes("opacity-70")
        ui.label(label).classes("tech-label-sub")
        ui.label().bind_text_from(stats, key).classes("tech-label-sub")


@ui.page("/listeners")
async def listeners():
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    setup_menu("Listeners")
    await listener_view()
    await build_footer()


async def listener_view():
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        with ui.row().classes("w-full items-center justify-between tech-header-bar"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("headphones", color="emerald-500").classes("text-xl")
                ui.label("LISTENERS //").classes("tech-label-header-section")

            with ui.row().classes("items-center gap-2"):
                with (
                    ui.button(on_click=start_listener_dialogue)
                    .classes("tech-btn-action px-2")
                    .props("dense flat size=sm")
                ):
                    ui.icon("add", size="xs").classes("mr-1")
                    ui.label("LISTENER").classes("tech-label-sub")
                    # ui.tooltip("Build New Payload")
                    formatted_tooltip(title="Start a new Listener")
                ui.button(icon="refresh", on_click=lambda: ui.navigate.to("/listeners")).props(
                    "dense flat size=sm"
                ).classes("tech-btn-action-2")

        # Stats row
        with ui.row().classes("w-full h-8 gap-0 bg-[#0c0c0c] border-b border-white/5 items-center"):
            stat_widget("Total:", "router", "emerald", "total")
            stat_widget("Online:", "wifi", "green", "online")
            # stat_widget("HTTP", "public", "blue", "http")

        with ui.column().classes("w-full p-0 flex-grow overflow-hidden"):
            await render_listeners_table()


async def render_listeners_table():
    # searchbar
    with ui.row().classes("w-full items-center px-2 py-1 bg-white/2"):
        filter_text = (
            ui.input(placeholder="Filter...")
            .props("dense dark border color=emerald input-class=text-emerald-400 hide-bottom-space")
            .classes("w-150 tech-input items-center")
        )
        with filter_text.add_slot("prepend"):
            ui.icon("arrow_forward_ios", size="xs", color="emerald-500")
        with filter_text:
            formatted_tooltip("Filter artifacts", "A simple text based filter search. Not Lucene, sorry.")

    columns = [
        {"name": "status", "label": "STATUS", "field": "status", "align": "left", "sortable": True},
        {"name": "name", "label": "NAME", "field": "name", "align": "left", "sortable": True},
        {
            "name": "listener UUID",
            "label": "LISTENER UUID",
            "field": "listener_uuid",
            "align": "left",
            "sortable": True,
        },
        {"name": "type", "label": "PROTOCOL", "field": "type", "align": "left", "sortable": True},
        {"name": "bind", "label": "BIND ADDRESS", "field": "bind", "align": "left", "sortable": True},
        {"name": "profile", "label": "PROFILE", "field": "profile", "align": "left", "sortable": True},
        {"name": "notes", "label": "NOTES", "field": "notes", "align": "left"},
    ]

    table = (
        ui.table(columns=columns, rows=[], row_key="id", selection="multiple", pagination=15)
        # .classes("w-full bg-transparent no-shadow text-neutral-300 flex-grow sticky-header")
        .classes("w-full flex-grow tech-table-base tech-table-head tech-table-body tech-table-row-hover")
        .props("dense")
        .bind_filter_from(filter_text, "value")
    )
    # this should be at the top, but for now it's here cuz it's only called in the table.on
    current_uri = await get_current_uri()
    table.on(
        # double click to go to implant page
        "row-dblclick",
        lambda e: ui.timer(0.1, lambda: navigate(f"/listener/{e.args[1]['listener_uuid']}", current_uri), once=True),
    )

    # and select on single click
    def toggle_selection(e):
        row_data = e.args[1]
        if row_data in table.selected:
            table.selected.remove(row_data)
        else:
            table.selected.append(row_data)
        table.update()  # Refresh UI to show the checkmark

    table.on("row-click", toggle_selection)

    async def update_table_data():
        try:
            resp = await get_all_listener_data()
            fresh_data = resp if isinstance(resp, list) else resp.get("data", [])

            new_rows = []
            o_count = 0

            for listener in fresh_data:
                active = bool(listener.get("listener_active", 0))
                l_type = listener.get("listener_type", "raw")
                if active:
                    o_count += 1

                new_rows.append(
                    {
                        "id": listener.get("listener_uuid"),
                        "status": active,
                        "name": listener.get("listener_name", "Unknown"),
                        "type": l_type,
                        "bind": f"{listener.get('listener_host', '0.0.0.0')}:{listener.get('listener_port', '0')}",
                        "profile": listener.get("listener_profile_name", "Default"),
                        "notes": listener.get("listener_notes", ""),
                        "listener_uuid": listener.get("listener_uuid"),
                    }
                )

            stats.update({"total": len(new_rows), "online": o_count})
            table.rows = new_rows
        except Exception as e:
            server_log.error(f"Table Update Failed: {e}")

    update_time = app.storage.user.get("auto_refresh_rate", 2)
    ui.timer(update_time, update_table_data)
    await update_table_data()

    # adds in space for checkbox in table
    table.add_slot(
        "header",
        r"""
    <q-tr :props="props" class="bg-white/5 text-neutral-400 uppercase text-xs tracking-wider border-b border-white/10">
        <q-th auto-width>
            <q-checkbox dense size="sm" v-model="props.selected" />
        </q-th>
        <q-th v-for="col in props.cols" :key="col.name" :props="props">
            {{ col.label }}
        </q-th>
    </q-tr>
    """,
    )

    table.add_slot(
        "body-cell-status",
        r"""
        <q-td :props="props">
            <div class="row items-center gap-2">
                <div :class="props.row.status ? 'w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse' : 'w-1.5 h-1.5 rounded-full bg-red-900 opacity-50'"></div>
                <span :class="props.row.status ? 'text-[9px] font-bold text-emerald-500' : 'text-[9px] font-bold text-red-900 opacity-50'">
                    {{ props.row.status ? 'ONLINE' : 'OFFLINE' }}
                </span>
            </div>
        </q-td>
    """,  # noqa
    )

    table.add_slot(
        "body-cell-type",
        r"""
        <q-td :props="props">
            <q-badge :color="props.value === 'raw' ? 'blue-10' : 'purple-10'" class="font-mono text-[9px] px-1 rounded-sm">{{ props.value.toUpperCase() }}</q-badge>
        </q-td>
    """,  # noqa
    )

    with ui.row().classes("w-full p-1 px-2 justify-end gap-2 border-t border-white/5 bg-white/2"):

        async def batch_action(action_func, msg, color):
            if not table.selected:
                return notify("No Selection", type="warning")
            for row in table.selected:
                await action_func(row["listener_uuid"])
            notify(f"{msg} {len(table.selected)} listeners", type=color)
            await update_table_data()
            return None

        with ui.button(
            "START",
            icon="play_arrow",
            on_click=lambda: batch_action(start_listener_from_existing, "Started", "positive"),
        ).props("flat dense color=green no-caps size=sm"):
            formatted_tooltip(
                title="Start a stopped listener",
                body=("The listener must already exist to be restarted."),
                footer="To spawn a new listener, click the '+ listener' button",
            )

        with ui.button(
            "RESTART", icon="restart_alt", on_click=lambda: batch_action(restart_listener, "Restarted", "positive")
        ).props("flat dense color=orange no-caps size=sm"):
            formatted_tooltip(
                title="Restart the Listener",
                body=(
                    "Kill the current listener process, and re-spawn a new one with the same config. "
                    "This is handy for if a listener crashes, or encounters a bug."
                ),
            )

        with ui.button("STOP", icon="stop", on_click=lambda: batch_action(stop_listener, "Stopped", "negative")).props(  # noqa
            "flat dense color=red no-caps size=sm"
        ):
            formatted_tooltip(
                title="Stop Listener",
                body=(
                    "Stops the listener process without deleting it.\n"
                    "The listener remains in the database,\n"
                    "is still a valid compile target,\n"
                    "and can be restarted at any time."
                ),
                footer="(Acts like a pause button)",
            )

        with ui.button(
            "DELETE", icon="delete", on_click=lambda: batch_action(delete_listener, "Delete listener", "positive")
        ).props("flat dense color=purple no-caps size=sm"):
            # ui.tooltip("Stop, and DELETE a listener from the database. This listener will cease to exist.")
            formatted_tooltip(
                title="Delete Listener",
                body=(
                    "Stops, and deletes the listener from the Database.\n"
                    "The listener will be nuked from existence via this action"
                ),
                footer="\n",  # add a \n so there's space at the bottom, and the whole message shows.
            )


# ====================
#   DIALOG LOGIC
# ====================
async def start_listener_dialogue():
    profile_names = await _get_profile_list()

    async def _start_listener():
        # Define what protocols don't need network binding
        is_pivot = listener_type_field.value == "pivot_smb"

        # only check host/port if NOT a pivot
        required_fields = [listener_name_field.value]
        if not is_pivot:
            required_fields.extend([listener_host_field.value, listener_port_field.value])

        if not all(required_fields):
            notify("Missing required fields", type="warning", color="orange-9")
            return

        selected_profile = str(listener_profile_field.value)
        profile_contents = await _get_profile_contents(selected_profile)
        if not profile_contents:
            notify(f"Profile not found: {selected_profile}", type="warning")
            return

        # set defaults if not host or port
        # this is important if we are a pivot listener.
        final_host = "localhost" if is_pivot else listener_host_field.value
        final_port = 0 if is_pivot else int(listener_port_field.value)

        dialog_spinner.visible = True

        result = await start_listener(
            listener_host=final_host,
            listener_port=int(final_port),
            listener_type=listener_type_field.value,
            listener_name=listener_name_field.value,
            listener_notes=listener_notes_field.value,
            listener_profile_name=selected_profile,
            listener_profile_contents=profile_contents,
        )

        dialog_spinner.visible = False

        if result:
            notify("Listener Online", type="positive", color="emerald-9")
            dialog.close()
            # ui.navigate.to("/listeners")
        else:
            notify("Failed to start listener", type="negative")

    # TECH DIALOG
    with ui.dialog() as dialog, ui.card().classes("tech-dialog w-[600px] p-0 rounded overflow-hidden"):
        with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
            with ui.row().classes("gap-2 items-center"):
                ui.icon("rss_feed", color="emerald-500")
                ui.label("NEW LISTENER").classes("tech-label-sub")
            ui.button(icon="close", on_click=dialog.close).props("dense flat size=sm color=grey")

        with ui.column().classes("p-6 gap-6 w-full"):
            with ui.row().classes("w-full gap-4"):
                listener_name_field = (
                    ui.input("LISTENER NAME").props("outlined dense dark color=emerald").classes("flex-1 tech-input")
                )

                listener_type_field = (
                    ui.select(["raw", "pivot_smb"], label="PROTOCOL", value="raw")
                    .props("outlined dense dark color=emerald options-dense")
                    .classes("w-1/3 tech-select")
                )

            with ui.row().classes("w-full gap-4"):
                listener_host_field = (
                    ui.input("BIND HOST").props("outlined dense dark color=emerald").classes("flex-1 tech-input")
                )
                with listener_host_field:
                    # ui.tooltip("External IP/Hostname (No 0.0.0.0)")
                    formatted_tooltip(
                        title="Listener Host",
                        body="The IP/Address the listener will listen on",
                        footer="DO NOT put 0.0.0.0, the listener must bind to an IP/Hostname",
                    )

                # Bind visibility: Show only if type is NOT 'pivot_smb'
                listener_host_field.bind_visibility_from(
                    listener_type_field, "value", backward=lambda v: v != "pivot_smb"
                )

                listener_port_field = (
                    ui.input(
                        label="PORT",
                        placeholder="80",
                        validation={
                            "Invalid": lambda v: (
                                True  # exclude pivot_smb from this check cuz it doesn't ahve a port
                                if listener_type_field.value == "pivot_smb"
                                else (v.isdigit() and 1 <= int(v) <= 65535)
                            )
                        },
                    )
                    .props("outlined dense dark type=number color=emerald")
                    .classes("w-32")
                )
                #  Bind visibility for port as well
                listener_port_field.bind_visibility_from(
                    listener_type_field, "value", backward=lambda v: v != "pivot_smb"
                )

            with ui.row().classes("w-full gap-2 items-end"):
                listener_profile_field = (
                    ui.select(
                        profile_names,
                        label="NETWORK PROFILE",
                        with_input=True,
                    )
                    .props("outlined dense dark color=emerald options-dense")
                    .classes("flex-grow tech-select")
                )
                ui.button(
                    icon="upload_file",
                    on_click=lambda: _upload_profile_dialog(listener_profile_field),
                ).props("flat dense size=sm color=emerald").tooltip("Upload Profile")

            listener_notes_field = (
                ui.textarea("OPERATIONAL NOTES")
                .props("outlined dark color=emerald input-class='h-32 resize-none'")  # Apply height directly to input
                .classes("w-full")  # Keep width on the wrapper
            )

        with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"):
            dialog_spinner = ui.spinner(size="sm", color="emerald-500")
            dialog_spinner.visible = False

            ui.button("CANCEL", on_click=dialog.close).props("flat dense color=grey no-caps")

            ui.button("SPAWN LISTENER", on_click=_start_listener).props(
                "unelevated dense color=emerald text-color=white no-caps"
            ).classes("font-bold tracking-wide")

    dialog.open()


async def _get_profile_list() -> list:
    """Fetch profile names from the server API."""
    try:
        resp = await get_all_profiles()
        if resp and resp.get("data"):
            return sorted([p["artifact_name"] for p in resp["data"]], key=str.lower)
    except Exception:
        pass
    return []


async def _get_profile_contents(profile_name: str) -> str:
    """Fetch profile contents from the server API."""
    try:
        resp = await get_profile_by_name(profile_name)
        if resp and resp.get("data", {}).get("artifact_contents"):
            return resp["data"]["artifact_contents"]
    except Exception:
        pass
    return ""


def _upload_profile_dialog(profile_select_field):
    """Open a dialog to upload a .toml profile file to the server."""
    state = {"filename": "", "contents": ""}

    async def handle_upload(e):
        try:
            file_bytes = await e.file.read()
            state["filename"] = e.file.name
            state["contents"] = file_bytes.decode("utf-8")
            submit_btn.enable()
        except Exception as err:
            notify(f"Failed to read file: {err}", type="negative")

    async def submit():
        if not state["contents"]:
            return
        name = state["filename"]
        if not name.endswith(".toml"):
            name += ".toml"

        submit_btn.props("loading")
        resp = await upload_profile(name, state["contents"])
        submit_btn.props(remove="loading")

        if resp:
            notify(f"Uploaded {name}", type="positive", color="emerald-9")
            d.close()
            new_names = await _get_profile_list()
            profile_select_field.options = new_names
            profile_select_field.set_value(name)
            profile_select_field.update()
        else:
            notify("Upload failed", type="negative")

    with ui.dialog() as d, ui.card().classes("tech-dialog w-[500px] p-0 rounded overflow-hidden"):
        with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
            with ui.row().classes("gap-2 items-center"):
                ui.icon("upload_file", color="emerald-500")
                ui.label("UPLOAD PROFILE").classes("tech-label-sub")
            ui.button(icon="close", on_click=d.close).props("dense flat size=sm color=grey")

        with ui.column().classes("p-5 gap-4 w-full"):
            ui.upload(
                label="SELECT .TOML PROFILE",
                auto_upload=True,
                max_files=1,
                on_upload=handle_upload,
            ).props("flat bordered dark color=emerald accept=.toml").classes("w-full bg-black/20")

        with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"):
            ui.button("CANCEL", on_click=d.close).props("flat dense color=grey no-caps")
            submit_btn = (
                ui.button("UPLOAD", on_click=submit)
                .props("unelevated dense color=emerald text-color=white no-caps")
                .classes("font-bold tracking-wide")
            )
            submit_btn.disable()

    d.open()
