import structlog
from nicegui import ui

from client.src.client.modules.api_calls import get_listener_data
from client.src.client.modules.profile_visualizer import http_view
from client.src.client.pages.footer import build_footer
from client.src.client.pages.formatted_tooltip import formatted_tooltip
from client.src.client.pages.menu import setup_menu

server_log = structlog.getLogger("server")


# ========================================
#   DASHBOARD WIDGETS
# ========================================
def flat_stat(label: str, value: str, icon: str, color: str = "emerald"):
    """Flat, inline stat widget against the background"""
    with ui.element("div").classes(
        "flex-1 h-full px-4 gap-2 flex items-center border-r border-white/5 bg-transparent min-w-max"
    ):
        ui.icon(icon, size="14px", color=f"{color}-500").classes("opacity-70")
        ui.label(label).classes("tech-label-sub")
        ui.label(str(value)).classes("text-[11px] font-mono text-neutral-200")


def info_row(key: str, value: str):
    """Key-Value terminal row"""
    with ui.row().classes(
        "w-full justify-between items-center py-2 border-b border-white/5 hover:bg-white/5 transition-colors"
    ):
        ui.label(key).classes("tech-label-sub")
        ui.label(str(value)).classes("text-xs font-mono text-neutral-300 break-all text-right max-w-[60%]")


# ========================================
#   PAGE LOGIC
# ========================================


@ui.page("/listener/{listener_uuid}")
async def listener_details(listener_uuid: str):
    # Layout Setup
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("listener View")

    # Fetch listener listener_data
    api_res = await get_listener_data(listener_uuid)
    listener_data = api_res.get("data", {}) or {}

    # Render Dashboard
    await render_dashboard(listener_data, listener_uuid)
    await build_footer()


# ========================================
# dashboard
# ========================================
async def render_dashboard(listener_data: dict, listener_uuid: str):
    profile_toml = listener_data.get("listener_profile_contents", "")

    # MAIN CONTAINER
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        # ====================
        #   1. HEADER
        # ====================
        with ui.row().classes("w-full p-4 border-b border-white/5 bg-black/40 items-center justify-between shrink-0"):
            with ui.row().classes("items-center gap-4"):
                ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/operations")).props(
                    "flat dense square size=sm color=grey"
                )
                ui.icon("terminal", size="md", color="emerald-500").classes(
                    "p-2 bg-emerald-500/10 rounded border border-emerald-500/20"
                )
                with ui.column().classes("gap-0"):
                    ui.label(f"{listener_uuid}").classes(
                        "text-sm font-bold tracking-[0.2em] text-white font-mono uppercase"
                    )
                    ui.label(f"listener // {listener_data.get('listener_host', '0.0.0.0')}").classes(
                        "text-[12px] font-mono text-emerald-500 tracking-[0.2em]"
                    )

            with ui.row().classes("items-center gap-2"):
                btn_start = ui.button(icon="play_arrow", on_click=lambda: ...).props(
                    "dense flat size=sm color=emerald-400"
                )
                with btn_start:
                    formatted_tooltip("Start")
                btn_restart = ui.button(icon="restart_alt", on_click=lambda: ...).props(
                    "dense flat size=sm color=blue-400"
                )
                with btn_restart:
                    formatted_tooltip("Restart", body="Attempts to restart the given service")

                btn_stop = ui.button(icon="stop", on_click=lambda: ...).props("dense flat size=sm color=red-400")
                with btn_stop:
                    formatted_tooltip("Stop", body="Attempts to stop the given service")

        # ====================
        #   2. VITALS BAR (Flat layout replacing stat_cards)
        # ====================
        with ui.row().classes(
            "w-full h-10 gap-0 bg-black/20 border-b border-white/5 items-center shrink-0 flex-nowrap overflow-x-auto"
        ):
            flat_stat("NETWORK ADDR", listener_data.get("listener_host", "0.0.0.0"), "lan", "blue")
            flat_stat("NETWORK PORT", listener_data.get("listener_port", "0"), "lan", "blue")
            flat_stat("NETWORK PROFILE", listener_data.get("listener_profile_name", "0.0.0.0"), "lan", "blue")
            flat_stat("CONNECTED IMPLANTS", listener_data.get("?", "?"), "lan", "blue")

        # ====================
        #   3. BODY
        # ====================
        with ui.row().classes("w-full flex-grow p-4 gap-4 overflow-hidden no-wrap items-stretch"):  # noqa - nicegui nested
            # --------------------
            # LEFT: WORKSPACE / TABS (Removed ui.card)
            # --------------------
            with ui.column().classes(
                "flex-grow min-w-0 bg-black/20 border border-white/5 rounded overflow-hidden flex-nowrap gap-0"
            ):
                # Tabs Header
                with ui.row().classes("w-full border-b border-white/5 bg-black/40 px-2 shrink-0"):
                    tabs = (
                        ui.tabs()
                        .classes("w-full text-left")
                        .props(
                            "dense indicator-color=emerald text-color=grey-5 active-color=emerald-400 align=left narrow-indicator"  # noqa
                        )
                    )
                    with tabs:
                        ui.tab("metadata_tab", label="Listener Data").classes("h-10 min-h-0 tech-label-sub")

                        ui.tab("connected_implants_tab", label="CONNECTED IMPLANTS").classes(
                            "h-10 min-h-0 tech-label-sub"
                        )
                        ui.tab("network_profile_tab", label="Net Profile [CONFIG]").classes(
                            "h-10 min-h-0 tech-label-sub"
                        )
                        ui.tab("network_profile_wire_tab", label="Net Profile [On Wire]").classes(
                            "h-10 min-h-0 tech-label-sub"
                        )

                        # ui.tab("graph_tab", label="GRAPH").classes("h-10 min-h-0 tech-label-sub")

                # Tabs Content
                with ui.tab_panels(tabs, value="metadata_tab").classes("w-full flex-grow bg-transparent p-0"):
                    # Metadata Tab
                    with ui.tab_panel("metadata_tab").classes("w-full h-full p-0"):  # noqa
                        with ui.scroll_area().classes("w-full h-full p-4"):
                            for key, value in listener_data.items():
                                # skip contents, it's way too big
                                if key == "listener_profile_contents":
                                    info_row(key, "See `NET PROFILE [CONFIG]` tab")
                                    continue
                                info_row(key, value)

                    # Metadata Tab
                    with ui.tab_panel("connected_implants_tab").classes(
                        "w-full h-full items-center justify-center text-neutral-600"
                    ):  # noqa
                        ui.icon("hub", size="xl").classes("mb-2 opacity-50")
                        ui.label("connected implants NOT IMPLEMENTED").classes("tech-label-sub")

                    # network_profile_tab
                    with ui.tab_panel("network_profile_tab").classes("w-full h-full p-0"):
                        # using a UI log, it has builtins like scrolling, etc to make this easier.
                        # not a permanent solution, but works for now.
                        code_panel = ui.codemirror(profile_toml, theme="androidstudio", language="TOML").classes(
                            "w-full h-full"
                        )  # noqa
                        # sets panel to readonly
                        code_panel.set_enabled(False)

                    with ui.tab_panel("network_profile_wire_tab").classes("w-full h-full p-0"):
                        # using a UI log, it has builtins like scrolling, etc to make this easier.
                        # not a permanent solution, but works for now.
                        code_panel = ui.log().classes("w-full h-full")  # noqa
                        profile_rep = http_view(profile_toml)
                        for line in profile_rep:
                            code_panel.push(line)
                    # Graph Tab
                    # with ui.tab_panel("graph_tab").classes(
                    #     "w-full h-full items-center justify-center text-neutral-600"
                    # ):
                    #     ui.icon("hub", size="xl").classes("mb-2 opacity-50")
                    #     ui.label("GRAPH MODULE NOT IMPLEMENTED").classes("tech-label-sub")

                # Footer Actions
                with ui.column().classes("w-full p-4 gap-2 border-t shrink-0"):
                    ui.label("ACTIONS").classes("tech-label-sub")
                    # with ui.row().classes("w-full gap-2"):
                    # ui.button("KILL", icon="bolt").classes(
                    #     "flex-1 bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20 transition-colors"  # noqa
                    # ).props("unelevated dense")
                    # ui.button("EXIT", icon="logout").classes(
                    #     "!tech-btn-action w-full"  # noqa
                    # ).props("unelevated dense")
