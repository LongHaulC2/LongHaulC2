import asyncio

import hexdump
import structlog
from nicegui import app, ui

from client.modules.api_calls import get_payload_bytes, get_payload_data
from client.pages.components.metadata_view import MetadataView
from client.pages.custom import BongoSpinner

# Adjust these imports based on your actual file structure for payloads
from client.pages.footer import build_footer
from client.pages.formatted_tooltip import formatted_tooltip
from client.pages.menu import setup_menu
from client.pages.payloads import download_payload, download_payload_source

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


@ui.page("/payload/{payload_hash}")
async def payload_details(payload_hash: str):
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Payload View")

    # Fetch payload specific data
    # note - there is no GET one payload for, that is reserved for getting the actual payload bytes
    # We'll have to get ALL the payloads, then sort for the one we want.
    # not super efficent, but ideally there wouldn't be enough payloads that this
    # actually slows anything down.
    # Additionally - payloads are not stored in neo4j, but instead in mysql, so we can't do any fancy graph queries
    # to get this data, we just have to ask for it directly.
    response_data = await get_payload_data()
    payload_list = response_data.get("data", [])

    # for some stupid reason I made this api endpoint return a list, so we get to iter over it. yay
    # again, shouldn't be too bad on performance, but is not ideal.
    payload_metadata = {}
    for payload_data in payload_list:
        _payload_hash = payload_data.get("payload_hash")

        if _payload_hash == payload_hash:
            payload_metadata = payload_data
            break

    await render_dashboard(payload_metadata, payload_hash)
    await build_footer()


async def render_dashboard(payload_metadata: dict, payload_hash: str):
    # should get payload at load as well, for various metrics
    payload_bytes = await get_payload_bytes(payload_hash)

    payload_name = payload_metadata.get("payload_name", "?")
    payload_type = get_payload_type(payload_metadata)
    payload_size = round((len(payload_bytes) / 1000), 2)

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

                # Changed icon to memory/extension to fit "payload" vibe
                ui.icon("code", size="sm", color="emerald-500").classes(
                    "p-2 bg-emerald-500/10 rounded border border-emerald-500/20"
                )
                with ui.column().classes("gap-0"):
                    ui.label(f"{payload_name}").classes("tech-label-header-bold")
                    ui.label(f"payload_hash // {payload_hash}").classes("tech-label-sub text-emerald-500")

            # Actions right side area
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "SOURCE",
                    icon="code",
                    on_click=lambda: download_payload_source(hash=payload_hash, name=payload_name),
                ).props("dense flat size=sm").classes("tech-btn-action-2")
                ui.button(
                    "DOWNLOAD", icon="download", on_click=lambda: download_payload(hash=payload_hash, name=payload_name)
                ).props("dense flat size=sm").classes("tech-btn-action-2")

        with ui.row().classes(
            "w-full h-10 gap-0 bg-black/20 border-b border-white/5 items-center shrink-0 flex-nowrap overflow-x-auto"
        ):
            # Adapted flat stats for payload characteristics
            flat_stat("TYPE", payload_type, "extension", "emerald")
            flat_stat("SIZE (KB)", payload_size, "data_usage", "blue")
            flat_stat("OS TARGET", payload_metadata.get("os", "Windows"), "desktop_windows", "purple")
            flat_stat("ARCH", payload_metadata.get("arch", "x64"), "dns", "grey")

        with ui.row().classes("w-full flex-grow p-4 gap-4 overflow-hidden no-wrap items-stretch"):  # noqa
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
                        ui.tab("hexdump_tab", label="HEXDUMP").classes("h-10 min-h-0 tech-label-sub")
                        # ui.tab("strings_tab", label="STRINGS").classes("h-10 min-h-0 tech-label-sub")

                with ui.tab_panels(tabs, value="metadata_tab").classes("w-full flex-grow bg-transparent p-0"):
                    # --- METADATA TAB ---
                    with ui.tab_panel("metadata_tab").classes("w-full h-full p-0"):  # noqa - nicegui
                        MetadataView(payload_metadata)

                    # --- HEXDUMP TAB ---
                    with ui.tab_panel("hexdump_tab").classes("w-full h-full p-0 flex flex-col"):
                        with ui.column().classes("w-full"):
                            spinner = BongoSpinner("Processing hexdump (this may take a moment)...")
                            code_mirror = ui.codemirror(
                                value="Loading data...", theme="androidstudio", language="yaml"
                            ).classes("w-full h-full bg-transparent text-emerald-400 font-mono text-xs")

                            async def load_hexdump():
                                # gives control back to nicegui, so the tab can be switched to
                                # THEN, it does the whole "fetching/processing" message, so the user can see it
                                await asyncio.sleep(0.1)

                                # code_mirror.value = "Fetching bytes..."

                                # get data
                                data = await get_payload_bytes(payload_hash=payload_hash)

                                # once done, show that we are now processing
                                # code_mirror.value = "Processing hexdump (this may take a moment)..."
                                # throw a spinner in there for dramatic effect lol
                                # with ui.element().classes("w-full h-full items-center justify-center"):
                                spinner.start()

                                # yeet to a thread so this can happen in the background, and not freeze UI
                                hex_str = await asyncio.to_thread(hexdump.hexdump, data, result="return")
                                spinner.stop()

                                # update it back in main thread
                                code_mirror.value = hex_str

                        # Trigger load once directly on the main event loop
                        ui.timer(0, load_hexdump, once=True)

                    # payloads don't have a uuid... cuz they are in mysql
                    # with ui.tab_panel("notes_tab").classes("w-full h-full p-0"):  # noqa - nicegui
                    #     # hook me into genetic update func that takes node type, and contents?
                    #     with ui.column().classes("w-full h-full relative"):
                    #         GenericNotesEditor(
                    #             node_type="payload",
                    #             node_id=payload_uuid,
                    #         )

                with ui.column().classes("w-full p-4 gap-2 border-t border-white/5 shrink-0 bg-black/20"):
                    ui.label("ACTIONS").classes("tech-label-sub")
                    # Put payload-specific actions here, like "Generate Shellcode", "Download", "Delete"


def get_payload_type(payload_metadata: dict) -> str:
    """
    Helper to not clog the render_dashboard func.

    Determines payload type based off of payload name. Only used
    for visuals in the payload dashboard
    """
    name = payload_metadata.get("payload_name", "").lower()

    if "." not in name:
        return "RAW"
    if name.endswith(".exe"):
        return "EXE"
    if name.endswith(".dll"):
        return "DLL"
    return "RAW"
