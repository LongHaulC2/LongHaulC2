import structlog
from nicegui import ui

from client.modules.api_calls import get_single_node_data
from client.pages.components.dashboard_widgets import back_button, flat_stat
from client.pages.components.metadata_view import MetadataView
from client.pages.components.notes_editor import GenericNotesEditor
from client.pages.footer import build_footer
from client.pages.menu import setup_menu

server_log = structlog.getLogger("server")


@ui.page("/network/{network_uuid}")
async def network_details(network_uuid: str):
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Network View")

    api_res = await get_single_node_data(node_type="network", node_uuid=network_uuid)
    network_data = api_res.get("data", {}) or {}

    await render_dashboard(network_data, network_uuid)
    await build_footer()


async def render_dashboard(network_data: dict, network_uuid: str):
    subnet = network_data.get("subnet", "UNKNOWN")
    gateway = network_data.get("gateway", "UNKNOWN")
    network_type = network_data.get("network_type", "UNKNOWN")

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        with ui.row().classes("tech-header-bar flex w-full items-center justify-between shrink-0"):
            with ui.row().classes("items-center gap-4"):
                await back_button()
                ui.icon("router", size="sm", color="emerald-500").classes(
                    "p-2 bg-emerald-500/10 rounded border border-emerald-500/20"
                )
                with ui.column().classes("gap-0"):
                    ui.label(subnet).classes("tech-label-header-bold")
                    ui.label(f"NETWORK_UUID // {network_uuid}").classes("tech-label-sub text-emerald-500")

            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "INTERACT",
                    icon="terminal",
                    on_click=lambda: ui.navigate.to("/operations"),
                ).classes("tech-btn-action px-4").props("unelevated dense")

        with ui.row().classes(
            "w-full h-10 gap-0 bg-black/20 border-b border-white/5 items-center shrink-0 flex-nowrap overflow-x-auto"
        ):
            flat_stat("SUBNET", subnet, "lan", "emerald")
            flat_stat("GATEWAY", gateway, "router", "blue")
            flat_stat("TYPE", network_type, "dns", "orange")
            flat_stat("NET UUID", network_uuid, "fingerprint", "purple")

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
                ui.tab("metadata_tab", label="NETWORK DATA").classes("h-10 min-h-0 tech-label-sub")
                ui.tab("notes_tab", label="NOTES").classes("h-10 min-h-0 tech-label-sub")

        with ui.tab_panels(tabs, value="metadata_tab").classes("w-full flex-grow bg-transparent p-0 overflow-hidden"):
            with ui.tab_panel("metadata_tab").classes("w-full h-full p-0"):
                MetadataView(network_data)

            with (
                ui.tab_panel("notes_tab").classes("w-full h-full p-0"),
                ui.column().classes("w-full h-full relative"),
            ):
                GenericNotesEditor(
                    node_type="network",
                    node_id=network_uuid,
                )
