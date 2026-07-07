import structlog
from nicegui import ui

# Imports
from client.modules.api_calls import delete_file_from_server_filestore, get_all_files, get_file_bytes
from client.modules.navigate_hook import get_current_uri, navigate
from client.pages.components.dashboard_widgets import confirm_action
from client.pages.dialogues import upload_to_server_filestore_dialog
from client.pages.footer import build_footer
from client.pages.formatted_tooltip import formatted_tooltip
from client.pages.menu import setup_menu
from client.utils.helpers import notify

server_log = structlog.getLogger("server")


@ui.page("/filestore")
async def filestore():
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    setup_menu("Filestore")
    await filestore_view()
    await build_footer()


async def filestore_view():
    table = None

    async def upload_action():
        await upload_to_server_filestore_dialog()
        await refresh_data()

    async def refresh_data():
        if not table:
            return
        p_resp = await get_all_files()
        files = (p_resp or {}).get("data", [])
        rows = [
            {
                "file_name": p.get("file_name", "Unnamed"),
                "file_uuid": p.get("file_uuid"),
                "file_hash": p.get("file_hash", ""),
            }
            for p in files
        ]
        table.rows = rows

    async def do_delete():
        if not table:
            return
        file_uuids = [row["file_uuid"] for row in table.selected]
        for file_uuid in file_uuids:
            await delete_file_from_server_filestore(file_uuid)
        notify(f"Deleted {len(file_uuids)} file(s)", type="positive")
        table.selected.clear()
        await refresh_data()

    def delete_selected():
        if not table or not table.selected:
            notify("No files selected", type="warning")
            return
        count = len(table.selected)
        confirm_action(
            title="DELETE FILES",
            message=f"Permanently delete {count} file(s) from the server filestore?",
            on_confirm=do_delete,
            confirm_label="DELETE",
        )

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        with ui.row().classes("w-full items-center justify-between tech-header-bar"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("folder", color="emerald-500").classes("text-xl")
                ui.label("FILE STORE //").classes("tech-label-header-section")

            with ui.row().classes("items-center gap-2"):
                with ui.button(on_click=upload_action).props("dense flat size=sm").classes("tech-btn-action px-2"):
                    ui.icon("upload", size="xs").classes("mr-1")
                    ui.label("UPLOAD").classes("tech-label-sub")
                    formatted_tooltip(
                        "Upload File To Server File Store", footer="<i>Allows for multiple files at once</i>"
                    )

                with (
                    ui.button(icon="refresh", on_click=lambda: refresh_data())
                    .props("dense flat size=sm")
                    .classes("tech-btn-secondary")
                ):
                    formatted_tooltip("Refresh")

                with (
                    ui.button(icon="delete", on_click=delete_selected)
                    .props("dense flat size=sm square")
                    .classes("tech-btn-destructive")
                ):
                    formatted_tooltip("Delete Selected Files")

        with ui.column().classes("w-full p-0 flex-grow overflow-hidden"):
            current_uri = await get_current_uri()

            with ui.row().classes("w-full items-center px-2 py-1 bg-white/2"):
                filter_text = (
                    ui.input(placeholder="Filter...")
                    .props("dense dark border color=emerald input-class=text-emerald-400 hide-bottom-space")
                    .classes("w-150 tech-input items-center")
                )
                with filter_text.add_slot("prepend"):
                    ui.icon("arrow_forward_ios", size="xs", color="emerald-500")
                with filter_text:
                    formatted_tooltip("Filter files", "A simple text based filter search. Not Lucene, sorry.")

            columns = [
                {"name": "file_name", "label": "FILE NAME", "field": "file_name", "align": "left", "sortable": True},
                {"name": "file_uuid", "label": "FILE UUID", "field": "file_uuid", "align": "left", "sortable": True},
                {"name": "file_hash", "label": "HASH (MD5)", "field": "file_hash", "align": "left", "sortable": True},
                {"name": "actions", "label": "ACTIONS", "field": "actions", "align": "right"},
            ]

            table = (
                ui.table(columns=columns, rows=[], row_key="file_uuid", pagination=15, selection="multiple")
                .classes("w-full flex-grow tech-table-base tech-table-head tech-table-body tech-table-row-hover")
                .props("dense")
                .bind_filter_from(filter_text, "value")
            )

            table.add_slot(
                "header",
                r"""
                <q-tr :props="props" class="tech-table-head">
                    <q-th auto-width>
                        <q-checkbox v-model="props.selected" dense color="emerald" dark />
                    </q-th>
                    <q-th v-for="col in props.cols" :key="col.name" :props="props">{{ col.label }}</q-th>
                </q-tr>
            """,
            )

            table.add_slot(
                "no-data",
                r"""
            <div class="tech-empty-state w-full">
                <q-icon name="folder_open" size="xl" color="emerald-5" />
                <span class="tech-label-sub text-neutral-500">No files uploaded yet</span>
            </div>
            """,
            )

            table.add_slot(
                "body-cell-actions",
                r"""
                <q-td :props="props">
                    <div class="row items-center justify-end gap-1 no-wrap">
                        <q-btn icon="download" flat dense size="sm" color="grey-6" @click="$parent.$emit('bin', props.row)">
                            <q-tooltip class="bg-black">Download File</q-tooltip>
                        </q-btn>
                    </div>
                </q-td>
            """,  # noqa - table
            )

            table.on(
                "row-dblclick",
                lambda e: ui.timer(0.1, lambda: navigate(f"/file/{e.args[1]['file_uuid']}", current_uri), once=True),
            )
            table.on("bin", lambda e: download_file(file_uuid=e.args["file_uuid"], name=e.args["file_name"]))

            # and select on single click
            def toggle_selection(e):
                row_data = e.args[1]
                if row_data in table.selected:
                    table.selected.remove(row_data)
                else:
                    table.selected.append(row_data)
                table.update()  # Refresh UI to show the checkmark

            table.on("row-click", toggle_selection)

            await refresh_data()


async def download_file(file_uuid, name):
    file_bytes = await get_file_bytes(file_uuid)
    if file_bytes:
        ui.download(file_bytes, filename=f"{name}")
        notify("Transfer Complete", type="positive")
    else:
        notify("Transfer Failed", type="negative")
