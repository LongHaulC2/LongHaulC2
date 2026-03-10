import structlog
from nicegui import ui

# from client.src.client.modules.api_calls import get_network_data
from client.src.client.pages.footer import build_footer
from client.src.client.pages.menu import setup_menu

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


@ui.page("/network/{network_uuid}")
async def network_details(network_uuid: str):
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Network View")

    api_res = {}  # await get_network_data(network_uuid)
    network_data = api_res.get("data", {}) or {}

    await render_dashboard(network_data, network_uuid)
    await build_footer()


async def render_dashboard(network_data: dict, network_uuid: str):
    subnet = network_data.get("subnet", "UNKNOWN")
    gateway = network_data.get("gateway", "UNKNOWN")
    network_type = network_data.get("network_type", "UNKNOWN")
    # description = network_data.get("description", "UNKNOWN")

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        with ui.row().classes("tech-header-bar flex w-full items-center justify-between shrink-0"):
            with ui.row().classes("items-center gap-4"):
                ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/operations")).props(
                    "flat dense square size=sm"
                ).classes("tech-btn-ghost")
                ui.icon("router", size="md", color="emerald-500").classes(
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
            flat_stat("NET UUID", network_uuid[:8] + "...", "fingerprint", "purple")

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
                        ui.tab("metadata_tab", label="NETWORK DATA").classes("h-10 min-h-0 tech-label-sub")
                        ui.tab("hosts_tab", label="CONNECTED HOSTS").classes("h-10 min-h-0 tech-label-sub")

                with ui.tab_panels(tabs, value="metadata_tab").classes("w-full flex-grow bg-transparent p-0"):
                    with ui.tab_panel("metadata_tab").classes("w-full h-full p-0"):  # noqa - nicegu
                        with ui.scroll_area().classes("w-full h-full p-4"):
                            for key, value in network_data.items():
                                info_row(key, value)

                    with ui.tab_panel("hosts_tab").classes(
                        "w-full h-full items-center justify-center text-neutral-600"
                    ):
                        ui.icon("dns", size="xl").classes("mb-2 opacity-50")
                        ui.label("HOSTS MODULE NOT IMPLEMENTED").classes("tech-label-sub")

                with ui.column().classes("w-full p-4 gap-2 border-t border-white/5 shrink-0 bg-black/20"):
                    ui.label("ACTIONS").classes("tech-label-sub")
