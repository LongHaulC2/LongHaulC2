import structlog
from nicegui import ui

from client.modules.api_calls import (
    delete_file_from_server_filestore,
    get_all_files,
    get_file_bytes,
)
from client.pages.components.hex_view import GenericHexViewer
from client.pages.components.metadata_view import MetadataView
from client.pages.components.notes_editor import GenericNotesEditor
from client.pages.footer import build_footer
from client.pages.menu import setup_menu
from client.utils.helpers import notify

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


@ui.page("/file/{file_uuid}")
async def file_details(file_uuid: str):
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("File View")

    all_files_res = await get_all_files()
    all_files = (all_files_res or {}).get("data", [])

    file_data = {}
    for f in all_files:
        if f.get("file_uuid") == file_uuid:
            file_data = f
            break

    await render_dashboard(file_data, file_uuid)
    await build_footer()


async def render_dashboard(file_data: dict, file_uuid: str):
    file_contents = await get_file_bytes(file_uuid=file_uuid)
    file_name = file_data.get("file_name", "UNKNOWN")
    file_size = len(file_contents) / 1000
    md5_hash = file_data.get("file_hash", "UNKNOWN")
    # file_notes = file_data.get("file_notes", "NO NOTES")

    async def handle_download():
        file_bytes = await get_file_bytes(file_uuid)
        if file_bytes:
            ui.download(file_bytes, filename=file_name)
            notify("Transfer Complete", type="positive")
        else:
            notify("Transfer Failed", type="negative")

    async def handle_delete():
        await delete_file_from_server_filestore(file_uuid)
        notify("File deleted from server", type="warning")
        ui.navigate.to("/filestore")

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        with ui.row().classes("tech-header-bar flex w-full items-center justify-between shrink-0"):
            with ui.row().classes("items-center gap-4"):
                ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/filestore")).props(
                    "flat dense square size=sm"
                ).classes("tech-btn-ghost")
                ui.icon("description", size="sm", color="emerald-500").classes(
                    "p-2 bg-emerald-500/10 rounded border border-emerald-500/20"
                )
                with ui.column().classes("gap-0"):
                    ui.label(file_name).classes("tech-label-header-bold")
                    ui.label(f"FILE_UUID // {file_uuid}").classes("tech-label-sub text-emerald-500")

            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "DOWNLOAD",
                    icon="download",
                    on_click=handle_download,
                ).classes("tech-btn-action").props("dense flat size=sm")
                ui.button("DELETE FILE", icon="delete", on_click=handle_delete).props("dense flat size=sm").classes(
                    "tech-btn-action"
                )

        with ui.row().classes(
            "w-full h-10 gap-0 bg-black/20 border-b border-white/5 items-center shrink-0 flex-nowrap overflow-x-auto"
        ):
            flat_stat("FILE NAME", file_name, "description", "emerald")
            flat_stat("SIZE (KB)", file_size, "save", "blue")
            flat_stat("MD5", md5_hash, "fingerprint", "purple")

        with ui.row().classes("w-full flex-grow p-4 gap-4 overflow-hidden no-wrap items-stretch"):  # noqa - nicegui
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
                        ui.tab("metadata_tab", label="FILE DATA").classes("h-10 min-h-0 tech-label-sub")
                        ui.tab("preview_tab", label="HEX PREVIEW").classes("h-10 min-h-0 tech-label-sub")
                        ui.tab("notes_tab", label="NOTES TAB").classes("h-10 min-h-0 tech-label-sub")

                with ui.tab_panels(tabs, value="metadata_tab").classes("w-full flex-grow bg-transparent p-0"):
                    with ui.tab_panel("metadata_tab").classes("w-full h-full p-0"):  # noqa - nicegui
                        MetadataView(file_data)

                    with ui.tab_panel("preview_tab").classes("w-full h-full p-0 flex flex-col"):  # noqa - nicegui
                        with ui.column().classes("w-full h-full relative"):
                            GenericHexViewer(entity_id=file_uuid, fetch_bytes_api=get_file_bytes)

                    with ui.tab_panel("notes_tab").classes("w-full h-full p-0"):  # noqa - nicegui
                        # hook me into genetic update func that takes node type, and contents?
                        with ui.column().classes("w-full h-full relative"):
                            GenericNotesEditor(
                                node_type="file",
                                node_id=file_uuid,
                            )

                with ui.column().classes("w-full p-4 gap-2 border-t border-white/5 shrink-0 bg-black/20"):
                    ui.label("ACTIONS").classes("tech-label-sub")


async def notes_editor():
    ui.codemirror(theme="androidstudio").classes("w-full h-full")
