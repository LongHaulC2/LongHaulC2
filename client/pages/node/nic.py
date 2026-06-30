import structlog
from nicegui import ui

from client.modules.api_calls import get_single_node_data
from client.pages.components.dashboard_widgets import back_button, flat_stat
from client.pages.components.metadata_view import MetadataView
from client.pages.components.notes_editor import GenericNotesEditor
from client.pages.footer import build_footer
from client.pages.menu import setup_menu

server_log = structlog.getLogger("server")


@ui.page("/nic/{nic_uuid}")
async def nic_details(nic_uuid: str):
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("NIC View")

    api_res = await get_single_node_data(node_type="nic", node_uuid=nic_uuid)
    nic_data = api_res.get("data", {}) or {}

    await render_dashboard(nic_data, nic_uuid)
    await build_footer()


async def render_dashboard(nic_data: dict, nic_uuid: str):
    mac_address = nic_data.get("mac_address", "UNKNOWN")
    ip_address = nic_data.get("ip_address", "UNKNOWN")
    adapter_name = nic_data.get("adapter_name", "UNKNOWN")
    status = nic_data.get("status", "UNKNOWN")

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        with ui.row().classes("tech-header-bar flex w-full items-center justify-between shrink-0"):
            with ui.row().classes("items-center gap-4"):
                await back_button()
                ui.icon("settings_ethernet", size="sm", color="emerald-500").classes(
                    "p-2 bg-emerald-500/10 rounded border border-emerald-500/20"
                )
                with ui.column().classes("gap-0"):
                    ui.label(adapter_name).classes("tech-label-header-bold")
                    ui.label(f"NIC_UUID // {nic_uuid}").classes("tech-label-sub text-emerald-500")

            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "INTERACT",
                    icon="terminal",
                    on_click=lambda: ui.navigate.to("/operations"),
                ).classes("tech-btn-action px-4").props("unelevated dense")

        with ui.row().classes(
            "w-full h-10 gap-0 bg-black/20 border-b border-white/5 items-center shrink-0 flex-nowrap overflow-x-auto"
        ):
            flat_stat("MAC ADDRESS", mac_address, "fingerprint", "emerald")
            flat_stat("IP ADDRESS", ip_address, "lan", "blue")
            flat_stat("STATUS", status, "info", "orange")
            flat_stat("NIC UUID", nic_uuid[:8] + "...", "memory", "purple")

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
                ui.tab("metadata_tab", label="NIC DATA").classes("h-10 min-h-0 tech-label-sub")
                ui.tab("notes_tab", label="NOTES").classes("h-10 min-h-0 tech-label-sub")

        with ui.tab_panels(tabs, value="metadata_tab").classes("w-full flex-grow bg-transparent p-0 overflow-hidden"):
            with ui.tab_panel("metadata_tab").classes("w-full h-full p-0"):
                MetadataView(nic_data)

            with (
                ui.tab_panel("notes_tab").classes("w-full h-full p-0"),
                ui.column().classes("w-full h-full relative"),
            ):
                GenericNotesEditor(
                    node_type="nic",
                    node_id=nic_uuid,
                )
