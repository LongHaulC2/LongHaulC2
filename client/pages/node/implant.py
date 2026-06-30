import json
import time

import structlog
from nicegui import app, ui

from client.modules.api_calls import get_implant_data, get_implant_task_history
from client.pages.components.metadata_view import MetadataView
from client.pages.components.notes_editor import GenericNotesEditor
from client.pages.footer import build_footer
from client.pages.formatted_tooltip import formatted_tooltip
from client.pages.menu import setup_menu
from client.pages.operations import terminal

server_log = structlog.getLogger("server")


def flat_stat(label: str, value: str, icon: str, color: str = "emerald"):
    with ui.element("div").classes("tech-stat-pill flex-1 min-w-max"):
        ui.icon(icon, size="14px", color=f"{color}-500").classes("opacity-70")
        ui.label(label).classes("tech-label-sub")
        ui.label(str(value)).classes("tech-data-mono")


def info_row(key: str, value: str):
    with ui.row().classes(
        "w-full justify-between items-center py-2 border-b border-white/5 hover:bg-white/5 transition-colors"
    ):
        ui.label(key).classes("tech-label-sub")
        ui.label(str(value)).classes("tech-data-mono break-all text-right max-w-[60%]")


@ui.page("/implant/{implant_uuid}")
async def implant_details(implant_uuid: str):
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Implant View")

    api_res = await get_implant_data(implant_uuid)
    implant_metadata = api_res.get("data", {}) or {}

    await render_dashboard(implant_metadata, implant_uuid)
    await build_footer()


async def render_dashboard(implant_metadata: dict, implant_uuid: str):
    hostname = implant_metadata.get("system_hostname", "?")
    user = implant_metadata.get("user", "UNKNOWN")
    process_name = implant_metadata.get("process", "?")

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        with ui.row().classes("tech-header-bar flex w-full items-center justify-between shrink-0"):  # noqa
            with ui.row().classes("items-center gap-4"):
                await ui.context.client.connected()
                prev_uri = app.storage.tab.get("previous_uri", "/")
                with (
                    ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to(prev_uri))
                    .props("flat dense square size=sm")
                    .classes("tech-btn-ghost")
                ):
                    formatted_tooltip(prev_uri)
                ui.icon("terminal", size="sm", color="emerald-500").classes(
                    "p-2 bg-emerald-500/10 rounded border border-emerald-500/20"
                )
                with ui.column().classes("gap-0"):
                    ui.label(f"{user} @ {hostname}").classes("tech-label-header-bold")
                    ui.label(f"IMPLANT_UUID // {implant_uuid}").classes("tech-label-sub text-emerald-500")

            # disabling for now, this is the right side button area
            # with ui.row().classes("items-center gap-2"):
            #     ui.button(
            #         "INTERACT",
            #         icon="terminal",
            #         on_click=lambda: ui.navigate.to("/operations"),
            #     ).classes("tech-btn-action px-4").props("unelevated dense")

        with ui.row().classes(
            "w-full h-10 gap-0 bg-black/20 border-b border-white/5 items-center shrink-0 flex-nowrap overflow-x-auto"
        ):
            flat_stat("USER", user, "person", "emerald")
            flat_stat("EXT NETWORK ADDR", implant_metadata.get("external_ip", "0.0.0.0"), "lan", "blue")
            flat_stat(
                "PROCESS",
                process_name,
                "memory",
                "purple",
            )

            last_checkin = implant_metadata.get("last_checkin")
            sleep_value = implant_metadata.get("sleep_value")
            checkin_state = {"text": str(implant_metadata.get("last_seen", "Unknown"))}

            def update_checkin_display():
                if last_checkin and sleep_value:
                    now = int(time.time())
                    diff = (last_checkin + sleep_value) - now
                    if diff > 0:
                        checkin_state["text"] = f"Next in {diff}s"
                    else:
                        checkin_state["text"] = f"OVERDUE ({abs(diff)}s)"

            update_checkin_display()

            with ui.element("div").classes("tech-stat-pill flex-1 min-w-max"):
                ui.icon("schedule", size="14px", color="orange-500").classes("opacity-70")
                ui.label("NEXT CHECKIN").classes("tech-label-sub")
                checkin_label = ui.label(checkin_state["text"]).classes("tech-data-mono")

            if last_checkin and sleep_value:

                def tick_checkin():
                    update_checkin_display()
                    checkin_label.text = checkin_state["text"]

                update_time = app.storage.user.get("auto_refresh_rate", 1)
                ui.timer(update_time, tick_checkin)

            flat_stat("ARCH", implant_metadata.get("arch", "x64"), "dns", "grey")

        with ui.row().classes("w-full flex-grow p-4 gap-4 overflow-hidden no-wrap items-stretch"):  # noqa - nicegu
            with ui.column().classes(
                "flex-grow min-w-0 bg-black/20 border border-white/5 rounded overflow-hidden flex-nowrap gap-0"
            ):
                with ui.row().classes("w-full border-b border-white/5 bg-black/40 px-2 shrink-0"):
                    tabs = (
                        ui.tabs()
                        .classes("w-full text-left")
                        .props(
                            "dense indicator-color=emerald text-color=grey-5 active-color=emerald-400 align=left "
                            "narrow-indicator"
                        )
                    )
                    with tabs:
                        ui.tab("metadata_tab", label="METADATA").classes("h-10 min-h-0 tech-label-sub")
                        ui.tab("history_tab", label="COMMAND HISTORY").classes("h-10 min-h-0 tech-label-sub")
                        ui.tab("terminal_tab", label="TERMINAL").classes("h-10 min-h-0 tech-label-sub")
                        ui.tab("notes_tab", label="NOTES").classes("h-10 min-h-0 tech-label-sub")

                with ui.tab_panels(tabs, value="metadata_tab").classes("w-full flex-grow bg-transparent p-0"):
                    with ui.tab_panel("metadata_tab").classes("w-full h-full p-0"):  # noqa - nicegu
                        MetadataView(implant_metadata)

                    with ui.tab_panel("history_tab").classes("w-full h-full p-0 flex flex-col"):
                        # in one row, so large expands don't push the search to one side, and command table to another
                        with ui.row().classes(
                            "w-full p-2 justify-between items-center border-b border-white/5 shrink-0 bg-black/20"
                        ):
                            search = (
                                ui.input(placeholder="Search history...")
                                .props("dense dark border color=emerald input-class=text-emerald-400 hide-bottom-space")
                                .classes("w-150 tech-input items-center")
                            )
                            ui.button(icon="refresh", on_click=lambda: load_history()).props(
                                "flat dense square size=sm"
                            ).classes("tech-btn-ghost")
                            with search.add_slot("prepend"):
                                ui.icon("arrow_forward_ios", size="xs", color="emerald-500")

                            columns = [
                                {"name": "status", "label": "STATUS", "field": "status", "align": "left"},
                                {"name": "task", "label": "COMMAND", "field": "task", "align": "left"},
                                {"name": "id", "label": "UUID", "field": "id", "align": "left"},
                            ]

                            table = (
                                ui.table(columns=columns, rows=[], row_key="id")
                                .classes("tech-table-base w-full flex-grow")
                                .props("dense flat dark")
                            )

                            def apply_filter(e):
                                table._props["filter"] = e.value
                                table.update()

                            search.on_value_change(apply_filter)

                            table.add_slot(
                                "header",
                                r"""
                                <q-tr :props="props" class="tech-table-head">
                                    <q-th auto-width />
                                    <q-th v-for="col in props.cols" :key="col.name" :props="props" class="text-left">
                                        {{ col.label }}
                                    </q-th>
                                </q-tr>
                            """,
                            )

                            table.add_slot(
                                "body",
                                r"""
    <q-tr :props="props" class="tech-table-row-hover tech-table-body cursor-pointer" @click="props.expand = !props.expand">
        <q-td auto-width>
            <q-btn size="sm" color="emerald" round dense flat
                @click.stop="props.expand = !props.expand"
                :icon="props.expand ? 'remove' : 'add'" />
        </q-td>
        <q-td v-for="col in props.cols" :key="col.name" :props="props">
            <span v-if="col.name === 'status'">
                <q-icon :name="props.row.status_icon" :color="props.row.status_color" size="sm" class="mr-2"/>
                <span class="tech-data-mono">{{ col.value }}</span>
            </span>
            <span v-else-if="col.name === 'task'" class="tech-data-bold">
                {{ col.value }}
            </span>
            <span v-else class="tech-data-mono">
                {{ col.value }}
            </span>
        </q-td>
    </q-tr>
    <q-tr v-show="props.expand" :props="props">
        <q-td colspan="100%" class="bg-black/40 p-4 shadow-inner border-t border-white/5">
            <div class="flex flex-col gap-4">
                <div class="w-full">
                    <div class="tech-label-sub mb-1">REQUEST DATA //</div>
                    <pre class="w-full bg-transparent text-emerald-400 font-mono text-xs overflow-x-auto p-0 m-0">{{ props.row.req_data }}</pre>
                </div>
                <div class="w-full">
                    <div class="tech-label-sub mb-1">RESPONSE DATA //</div>
                    <pre class="w-full bg-transparent text-emerald-400 font-mono text-xs overflow-x-auto p-0 m-0">{{ props.row.res_data }}</pre>
                </div>
            </div>
        </q-td>
    </q-tr>
    """,  # noqa - nicegu
                            )

                        async def load_history():
                            res = await get_implant_task_history(implant_uuid)
                            tasks = res.get("data", [])

                            rows = []
                            for task in reversed(tasks):
                                task_req = task.get("task_request", {}) or {}
                                task_res = task.get("task_response")

                                task_name = task_req.get("task", {}).get("task_name", "UNKNOWN")
                                task_args = task_req.get("task", {}).get("args", {})
                                args_str = " ".join([f"{k}={v}" for k, v in task_args.items()])

                                full_cmd = task_name
                                if args_str:
                                    full_cmd += f" {args_str}"

                                is_complete = task_res is not None

                                rows.append(
                                    {
                                        "id": task.get("task_uuid", ""),
                                        "status": "Complete" if is_complete else "Pending",
                                        "task": full_cmd,
                                        "req_data": json.dumps(task_req, indent=2),
                                        "res_data": json.dumps(task_res, indent=2) if task_res else "No Response",
                                        "status_color": "positive" if is_complete else "warning",
                                        "status_icon": "check_circle" if is_complete else "pending",
                                    }
                                )

                            table.rows = rows
                            table.update()

                        ui.timer(0.1, load_history, once=True)

                    with ui.tab_panel("terminal_tab").classes(
                        "w-full h-full items-center justify-center text-neutral-600"
                    ):
                        await terminal(implant_uuid=implant_uuid)

                    with ui.tab_panel("notes_tab").classes("w-full h-full p-0"):  # noqa - nicegui
                        # hook me into genetic update func that takes node type, and contents?
                        with ui.column().classes("w-full h-full relative"):
                            GenericNotesEditor(
                                node_type="implant",
                                node_id=implant_uuid,
                            )

                with ui.column().classes("w-full p-4 gap-2 border-t border-white/5 shrink-0 bg-black/20"):
                    ui.label("ACTIONS").classes("tech-label-sub")
