from pathlib import Path

import structlog
from nicegui import ui

# Imports
from client.src.client.modules.api_calls import (
    get_all_listener_data,
    restart_listener,
    start_listener,
    start_listener_from_existing,
    stop_listener,
)
from client.src.client.pages.footer import build_footer
from client.src.client.pages.menu import setup_menu

stats = {"total": 0, "online": 0, "http": 0}

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
                ui.icon("rss_feed", color="emerald-500").classes("text-xl")
                ui.label("LISTENERS //").classes("tech-label-header-section")

            with ui.row().classes("items-center gap-2"):
                with (
                    ui.button(on_click=start_listener_dialogue)
                    .classes("tech-btn-action px-2")
                    .props("dense flat size=sm")
                ):
                    ui.icon("add", size="xs").classes("mr-1")
                    ui.label("LISTENER").classes("tech-label-sub")
                    ui.tooltip("Build New Payload")
                ui.button(icon="refresh", on_click=lambda: ui.navigate.to("/listeners")).props(
                    "dense flat size=sm"
                ).classes("tech-btn-action-2")

        # Stats row
        with ui.row().classes("w-full h-8 gap-0 bg-[#0c0c0c] border-b border-white/5 items-center"):
            stat_widget("Total", "router", "emerald", "total")
            stat_widget("Online", "wifi", "green", "online")
            stat_widget("HTTP", "public", "blue", "http")

        with ui.column().classes("w-full p-0 flex-grow overflow-hidden"):
            await render_listeners_table()


async def render_listeners_table():
    # searchbar
    with ui.row().classes("w-full items-center px-2 py-1 bg-white/2"):
        filter_text = (
            ui.input(placeholder="FILTER...")
            .props("outlined dense dark color=emerald input-class=text-[10px]")
            .classes("w-64 tech-input")
        )

    columns = [
        {"name": "status", "label": "STATUS", "field": "status", "align": "left", "sortable": True},
        {"name": "name", "label": "NAME", "field": "name", "align": "left", "sortable": True},
        {"name": "type", "label": "PROTOCOL", "field": "type", "align": "left", "sortable": True},
        {"name": "bind", "label": "BIND ADDRESS", "field": "bind", "align": "left", "sortable": True},
        {"name": "profile", "label": "PROFILE", "field": "profile", "align": "left", "sortable": True},
        {"name": "notes", "label": "NOTES", "field": "notes", "align": "left"},
    ]

    table = (
        ui.table(columns=columns, rows=[], row_key="id", selection="multiple", pagination=15)
        # .classes("w-full bg-transparent no-shadow text-neutral-300 flex-grow sticky-header")
        .classes("w-full flex-grow tech-table-base tech-table-head tech-table-body tech-table-row-hover")
        .bind_filter_from(filter_text, "value")
    )

    async def update_table_data():
        try:
            resp = await get_all_listener_data()
            fresh_data = resp if isinstance(resp, list) else resp.get("data", [])

            new_rows = []
            o_count = 0
            h_count = 0

            for listener in fresh_data:
                active = bool(listener.get("listener_active", 0))
                l_type = listener.get("listener_type", "http")
                if active:
                    o_count += 1
                if l_type == "http":
                    h_count += 1

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

            stats.update({"total": len(new_rows), "online": o_count, "http": h_count})
            table.rows = new_rows
        except Exception as e:
            server_log.error(f"Table Update Failed: {e}")

    ui.timer(2.0, update_table_data)
    await update_table_data()

    table.add_slot(
        "header",
        r"""
        <q-tr :props="props" class="bg-black/40 text-neutral-500 uppercase text-[10px] font-bold tracking-widest">
            <q-th v-for="col in props.cols" :key="col.name" :props="props">{{ col.label }}</q-th>
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
            <q-badge :color="props.value === 'http' ? 'blue-10' : 'purple-10'" class="font-mono text-[9px] px-1 rounded-sm">{{ props.value.toUpperCase() }}</q-badge>
        </q-td>
    """,  # noqa
    )

    with ui.row().classes("w-full p-1 px-2 justify-end gap-2 border-t border-white/5 bg-white/2"):

        async def batch_action(action_func, msg, color):
            if not table.selected:
                return ui.notify("No Selection", type="warning")
            for row in table.selected:
                await action_func(row["listener_uuid"])
            ui.notify(f"{msg} {len(table.selected)} listeners", type=color)
            await update_table_data()

        ui.button(
            "START",
            icon="play_arrow",
            on_click=lambda: batch_action(start_listener_from_existing, "Started", "positive"),
        ).props("flat dense color=green no-caps size=sm")
        ui.button(
            "RESTART", icon="restart_alt", on_click=lambda: batch_action(restart_listener, "Restarted", "positive")
        ).props("flat dense color=orange no-caps size=sm")
        ui.button("STOP", icon="stop", on_click=lambda: batch_action(stop_listener, "Stopped", "negative")).props(
            "flat dense color=red no-caps size=sm"
        )


# ====================
#   DIALOG LOGIC
# ====================
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

        file_path = Path(__file__).resolve().parent.parent / "user" / "profiles" / str(listener_profile_field.value)

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

    # TECH DIALOG
    with ui.dialog() as dialog, ui.card().classes("tech-dialog w-[600px] p-0 rounded overflow-hidden"):
        with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
            with ui.row().classes("gap-2 items-center"):
                ui.icon("rocket_launch", color="emerald-500")
                ui.label("INITIALIZE_listener").classes("tech-label-sub")
            ui.button(icon="close", on_click=dialog.close).props("dense flat size=sm color=grey")

        with ui.column().classes("p-6 gap-6 w-full"):
            with ui.row().classes("w-full gap-4"):
                listener_name_field = (
                    ui.input("LISTENER NAME").props("outlined dense dark color=emerald").classes("flex-1 tech-input")
                )

                listener_type_field = (
                    ui.select(["http", "ntp"], label="PROTOCOL", value="http")
                    .props("outlined dense dark color=emerald options-dense")
                    .classes("w-1/3 tech-select")
                )

            with ui.row().classes("w-full gap-4"):
                listener_host_field = (
                    ui.input("BIND HOST").props("outlined dense dark color=emerald").classes("flex-1 tech-input")
                )
                with listener_host_field:
                    ui.tooltip("External IP/Hostname (No 0.0.0.0)")

                listener_port_field = (
                    ui.input(
                        label="PORT",
                        placeholder="80",
                        validation={"Invalid": lambda v: v.isdigit() and 1 <= int(v) <= 65535},
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
                .classes("w-full tech-select")
            )

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


def get_malleable_profiles_list() -> list:
    try:
        script_path = Path(__file__).resolve().parent.parent / "user" / "profiles"
        script_path.mkdir(parents=True, exist_ok=True)
        return sorted((p.name for p in script_path.iterdir() if p.is_file()), key=str.lower)
    except Exception:
        return []


def get_malleable_profile_content(file_path) -> str:
    try:
        with open(file_path) as file:
            return file.read()
    except Exception:
        return ""
