import structlog
from nicegui import ui

from client.modules.api_calls import get_single_node_data
from client.pages.components.dashboard_widgets import back_button, flat_stat
from client.pages.components.metadata_view import MetadataView
from client.pages.components.notes_editor import GenericNotesEditor
from client.pages.footer import build_footer
from client.pages.menu import setup_menu

server_log = structlog.getLogger("server")


@ui.page("/host/{host_uuid}")
async def host_details(host_uuid: str):
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Host View")

    api_res = await get_single_node_data(node_type="host", node_uuid=host_uuid)
    host_data = api_res.get("data", {}) or {}

    await render_dashboard(host_data, host_uuid)
    await build_footer()


async def render_dashboard(host_data: dict, host_uuid: str):
    hostname = host_data.get("hostname", "UNKNOWN")
    first_seen = host_data.get("first_seen", "PLACEHOLDER_TIME")
    time_since = host_data.get("time_since_first_seen", "PLACEHOLDER_DURATION")

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        with ui.row().classes("tech-header-bar flex w-full items-center justify-between shrink-0"):
            with ui.row().classes("items-center gap-4"):
                await back_button()
                ui.icon("dns", size="sm", color="emerald-500").classes(
                    "p-2 bg-emerald-500/10 rounded border border-emerald-500/20"
                )
                with ui.column().classes("gap-0"):
                    ui.label(hostname).classes("tech-label-header-bold")
                    ui.label(f"HOST_UUID // {host_uuid}").classes("tech-label-sub text-emerald-500")

            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "INTERACT",
                    icon="terminal",
                    on_click=lambda: ui.navigate.to("/operations"),
                ).classes("tech-btn-action px-4").props("unelevated dense")

        with ui.row().classes(
            "w-full h-10 gap-0 bg-black/20 border-b border-white/5 items-center shrink-0 flex-nowrap overflow-x-auto"
        ):
            flat_stat("HOSTNAME", hostname, "dns", "emerald")
            flat_stat("FIRST SEEN", first_seen, "schedule", "orange")
            flat_stat("TIME SINCE", time_since, "history", "blue")
            flat_stat("HOST UUID", host_uuid[:8] + "...", "fingerprint", "purple")

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
                        ui.tab("metadata_tab", label="HOST DATA").classes("h-10 min-h-0 tech-label-sub")
                        ui.tab("notes_tab", label="NOTES").classes("h-10 min-h-0 tech-label-sub")

                with ui.tab_panels(tabs, value="metadata_tab").classes("w-full flex-grow bg-transparent p-0"):
                    with ui.tab_panel("metadata_tab").classes("w-full h-full p-0"):  # noqa
                        MetadataView(host_data)

                    with ui.tab_panel("notes_tab").classes("w-full h-full p-0"):  # noqa
                        with ui.column().classes("w-full h-full relative"):
                            GenericNotesEditor(
                                node_type="host",
                                node_id=host_uuid,
                            )

                with ui.column().classes("w-full p-4 gap-2 border-t border-white/5 shrink-0 bg-black/20"):
                    ui.label("ACTIONS").classes("tech-label-sub")
