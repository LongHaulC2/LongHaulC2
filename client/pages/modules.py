import json
import time

import structlog
from nicegui import ui

from client.modules.api_calls import (
    delete_module,
    get_all_modules,
    get_module_by_name,
    seed_modules,
    upload_module,
)
from client.modules.navigate_hook import get_current_uri, navigate
from client.pages.components.dashboard_widgets import confirm_action, stat_widget
from client.pages.footer import build_footer
from client.pages.formatted_tooltip import formatted_tooltip
from client.pages.menu import setup_menu
from client.utils.helpers import notify

server_log = structlog.getLogger("server")
module_stats = {"total": "0", "latest": "N/A"}


@ui.page("/modules")
async def modules_page():
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    setup_menu("Modules")
    await modules_view()
    await build_footer()


async def modules_view():
    refresh_ref = [None]

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        # HEADER
        with ui.row().classes("w-full items-center justify-between tech-header-bar"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("view_module", color="emerald-500").classes("text-xl")
                ui.label("MODULE_LIBRARY //").classes("tech-label-header-section")

            with ui.row().classes("items-center gap-2"):
                with (
                    ui.button(on_click=lambda: upload_module_dialog(refresh_ref))
                    .classes("tech-btn-action px-2")
                    .props("dense flat size=sm")
                ):
                    ui.icon("upload_file", size="xs").classes("mr-1")
                    ui.label("UPLOAD").classes("tech-label-sub")
                    formatted_tooltip(title="Upload a module JSON bundle")

                async def do_seed():
                    resp = await seed_modules()
                    if resp and resp.get("data"):
                        d = resp["data"]
                        notify(
                            f"Seeded: {d.get('created', 0)} new, {d.get('updated', 0)} updated",
                            type="positive",
                            color="emerald-9",
                        )
                        if refresh_ref[0]:
                            await refresh_ref[0]()
                    else:
                        notify("Seed failed", type="negative")

                with ui.button(on_click=do_seed).classes("tech-btn-action-2 px-2").props("dense flat size=sm"):
                    ui.icon("cloud_download", size="xs").classes("mr-1")
                    ui.label("SEED").classes("tech-label-sub")
                    formatted_tooltip(title="Seed default modules from server")

                with (
                    ui.button(icon="refresh", on_click=lambda: refresh_ref[0]())
                    .props("dense flat size=sm")
                    .classes("tech-btn-secondary")
                ):
                    formatted_tooltip("Refresh")

        with ui.row().classes("w-full h-8 gap-0 bg-[#0c0c0c] border-b border-white/5 items-center"):
            stat_widget("Total Modules:", "view_module", "emerald", "total", module_stats)
            stat_widget("Latest:", "history", "purple", "latest", module_stats)

        # CONTENT
        with ui.column().classes("w-full p-0 flex-grow overflow-hidden"):
            await render_modules_table(refresh_ref)


async def render_modules_table(refresh_ref):
    with ui.row().classes("w-full items-center px-2 py-1 bg-white/2"):
        filter_text = (
            ui.input(placeholder="Filter...")
            .props("dense dark border color=emerald input-class=text-emerald-400 hide-bottom-space")
            .classes("w-150 tech-input items-center")
        )
        with filter_text.add_slot("prepend"):
            ui.icon("arrow_forward_ios", size="xs", color="emerald-500")
        with filter_text:
            formatted_tooltip("Filter modules", "A simple text based filter search.")

    columns = [
        {"name": "name", "label": "Module Name", "field": "name", "align": "left", "sortable": True},
        {"name": "hash", "label": "HASH (SHA-256)", "field": "hash", "align": "left"},
        {"name": "updated", "label": "LAST UPDATED", "field": "updated", "align": "left", "sortable": True},
        {"name": "actions", "label": "ACTIONS", "field": "actions", "align": "right"},
    ]

    table = (
        ui.table(columns=columns, rows=[], row_key="name", pagination=15)
        .classes("w-full flex-grow tech-table-base tech-table-head tech-table-body tech-table-row-hover")
        .props("dense")
        .bind_filter_from(filter_text, "value")
    )

    current_uri = await get_current_uri()
    table.on(
        "row-dblclick",
        lambda _e: ui.timer(0.1, lambda: navigate("/module-builder", current_uri), once=True),
    )

    async def refresh_data():
        resp = await get_all_modules()
        modules_list = (resp or {}).get("data", [])

        rows = []
        for m in modules_list:
            updated_epoch = m.get("updated_at", 0)
            updated_str = time.strftime("%Y-%m-%d %H:%M", time.gmtime(updated_epoch / 1000)) if updated_epoch else "N/A"

            rows.append(
                {
                    "name": m.get("artifact_name", "Unnamed"),
                    "hash": m.get("content_hash", ""),
                    "updated": updated_str,
                }
            )

        table.rows = rows
        module_stats.update(
            {
                "total": str(len(rows)),
                "latest": rows[-1]["name"] if rows else "N/A",
            }
        )

    refresh_ref[0] = refresh_data
    await refresh_data()

    table.add_slot(
        "header",
        r"""
        <q-tr :props="props" class="tech-table-head">
            <q-th v-for="col in props.cols" :key="col.name" :props="props">{{ col.label }}</q-th>
        </q-tr>
    """,
    )

    table.add_slot(
        "no-data",
        r"""
    <div class="tech-empty-state w-full">
        <q-icon name="view_module" size="xl" color="emerald-5" />
        <span class="tech-label-sub text-neutral-500">No modules found — try seeding defaults</span>
    </div>
    """,
    )

    table.add_slot(
        "body-cell-hash",
        r"""
        <q-td :props="props">
            <span class="font-mono text-[11px] opacity-50 hover:opacity-100">{{ props.value }}</span>
        </q-td>
    """,
    )

    table.add_slot(
        "body-cell-actions",
        r"""
        <q-td :props="props">
            <div class="row items-center justify-end gap-1 no-wrap">
                <q-btn icon="download" flat dense size="sm" color="grey-6"
                       @click="$parent.$emit('download', props.row)">
                    <q-tooltip class="bg-black">DOWNLOAD JSON</q-tooltip>
                </q-btn>
                <q-btn icon="delete" flat dense size="sm" color="red-4" @click="$parent.$emit('del', props.row)">
                    <q-tooltip class="bg-black">DELETE</q-tooltip>
                </q-btn>
            </div>
        </q-td>
    """,
    )

    async def download_module(name):
        resp = await get_module_by_name(name)
        if resp and resp.get("data", {}).get("artifact_contents"):
            contents = resp["data"]["artifact_contents"]
            ui.download(contents.encode("utf-8"), filename=f"{name}.json")
            notify("Transfer Complete", type="positive")
        else:
            notify("Transfer Failed", type="negative")

    async def do_delete(name):
        resp = await delete_module(name)
        if resp:
            notify(f"Deleted {name}", type="positive", color="emerald-9")
            await refresh_data()
        else:
            notify("Delete failed", type="negative")

    table.on("download", lambda e: download_module(e.args["name"]))
    table.on(
        "del",
        lambda e: confirm_action(
            title="DELETE MODULE",
            message=f"Delete module '{e.args['name']}'? This cannot be undone.",
            on_confirm=lambda: do_delete(e.args["name"]),
            confirm_label="DELETE",
            icon="delete",
        ),
    )


def upload_module_dialog(refresh_ref):
    upload_state = {"filename": "", "contents": ""}

    async def handle_upload(e):
        try:
            file_bytes = await e.file.read()
            upload_state["filename"] = e.file.name
            upload_state["contents"] = file_bytes.decode("utf-8")
            try:
                bundle = json.loads(upload_state["contents"])
                module_name = bundle.get("module", {}).get("name", "")
                if module_name:
                    name_input.set_value(module_name)
            except json.JSONDecodeError:
                pass
            submit_btn.enable()
        except Exception as err:
            notify(f"Failed to read file: {err}", type="negative")

    async def submit():
        if not upload_state["contents"]:
            return
        name = (name_input.value or "").strip()
        if not name:
            notify("Enter a module name", type="warning", color="orange-9")
            return
        submit_btn.props("loading")
        resp = await upload_module(name, upload_state["contents"])
        submit_btn.props(remove="loading")
        if resp:
            notify(f"Uploaded {name}", type="positive", color="emerald-9")
            dlg.close()
            if refresh_ref[0]:
                await refresh_ref[0]()
        else:
            notify("Upload failed", type="negative")

    with ui.dialog() as dlg, ui.card().classes("tech-dialog w-[500px] p-0 rounded overflow-hidden"):
        with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
            with ui.row().classes("gap-2 items-center"):
                ui.icon("upload_file", color="emerald-500")
                ui.label("UPLOAD MODULE").classes("tech-label-sub")
            ui.button(icon="close", on_click=dlg.close).props("dense flat size=sm color=grey")

        with ui.column().classes("p-5 gap-4 w-full"):
            name_input = (
                ui.input(label="Module Name", placeholder="e.g. my_module")
                .props("outlined dense dark color=emerald")
                .classes("w-full tech-input")
            )
            ui.upload(
                label="SELECT MODULE JSON",
                auto_upload=True,
                max_files=1,
                on_upload=handle_upload,
            ).props("flat bordered dark color=emerald accept=.json").classes("w-full bg-black/20")

        with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"):
            ui.button("CANCEL", on_click=dlg.close).props("flat dense color=grey no-caps")
            submit_btn = (
                ui.button("UPLOAD", on_click=submit)
                .props("unelevated dense color=emerald text-color=white no-caps")
                .classes("font-bold tracking-wide")
            )
            submit_btn.disable()

    dlg.open()
