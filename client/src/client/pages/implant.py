import structlog
from nicegui import ui

from client.src.client.modules.api_calls import (
    get_implant_data,
    get_implant_task_history,
)
from client.src.client.pages.footer import build_footer
from client.src.client.pages.menu import setup_menu

server_log = structlog.getLogger("server")


# ========================================
#   DASHBOARD WIDGETS
# ========================================
def stat_card(label: str, value: str, icon: str, color: str = "emerald"):
    """Small dense stat widget"""
    with ui.card().classes("p-3 gap-1 bg-white/5 border border-white/10 rounded-sm no-shadow min-w-[140px] flex-grow"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(label).classes("tech-label-sub")
            ui.icon(icon, size="xs", color=f"{color}-500").classes("opacity-80")
        ui.label(value).classes("tech-label-sub")


def info_row(key: str, value: str):
    """Key-Value terminal row"""
    with ui.row().classes(
        "w-full justify-between items-center py-1 border-b border-white/5 hover:bg-white/5 transition-colors"
    ):
        ui.label(key).classes("tech-label-sub")
        ui.label(str(value)).classes("tech-label-sub")


# ========================================
#   PAGE LOGIC
# ========================================


@ui.page("/implant/{implant_uuid}")
async def implant_details(implant_uuid: str):
    # Layout Setup
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Operations")

    # Fetch Implant Metadata
    api_res = await get_implant_data(implant_uuid)
    data = api_res.get("data", {})

    # Fallback Data
    if not data:
        data = {
            "implant_uuid": implant_uuid,
            "computer_name": "UNKNOWN_HOST",
            "user_name": "N/A",
            "ip_address": "0.0.0.0",
            "os_details": "Unknown OS",
            "process_id": "0000",
            "process_name": "unknown.exe",
            "sleep": "60",
            "jitter": "10",
            "last_seen": "Never",
            "listener_url": "http://localhost:80",
            "arch": "x64",
        }

    # Render Dashboard
    await render_dashboard(data, implant_uuid)
    await build_footer()


# ========================================
# dashboard
# ========================================
async def render_dashboard(data: dict, implant_uuid: str):
    hostname = data.get("computer_name", "DESKTOP-UNKNOWN")
    user = data.get("user_name", "SYSTEM")

    # MAIN CONTAINER
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        # ====================
        #   1. HEADER (Fixed Height)
        # ====================
        with ui.row().classes("w-full p-4 border-b border-white/10 bg-black/20 items-center justify-between shrink-0"):
            with ui.row().classes("items-center gap-4"):
                ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/operations")).props(
                    "flat dense round size=sm color=grey"
                )
                ui.icon("computer", size="md", color="emerald-500").classes(
                    "p-2 bg-emerald-500/10 rounded border border-emerald-500/20"
                )
                with ui.column().classes("gap-0"):
                    with ui.row().classes("items-center gap-2"):
                        ui.label(hostname).classes("tech-label-sub")
                        with ui.row().classes(
                            "items-center gap-1 bg-emerald-900/30 px-2 rounded-full border border-emerald-500/30"
                        ):
                            ui.element("div").classes("w-2 h-2 rounded-full bg-emerald-400 animate-pulse")
                            ui.label("ONLINE").classes("tech-label-sub")
                    ui.label(f"UUID: {implant_uuid}").classes("tech-label-sub")

            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "INTERACT",
                    icon="terminal",
                    on_click=lambda: ui.navigate.to("/operations"),
                ).classes("tech-btn-action px-4").props("unelevated dense")

        # ====================
        #   2. BODY (Fills remaining height)
        # ====================
        with ui.column().classes("w-full flex-grow p-6 gap-6 overflow-hidden"):
            # ROW 1: VITALS (Fixed Height)
            with ui.row().classes("w-full gap-4 flex-nowrap overflow-x-auto pb-1 shrink-0"):
                stat_card("PRIMARY USER", user, "person")
                stat_card("NETWORK ADDR", data.get("ip_address"), "lan")
                stat_card(
                    "PROCESS ID",
                    f"{data.get('process_id')} ({data.get('process_name')})",
                    "memory",
                )
                stat_card("LAST SEEN", data.get("last_seen"), "schedule", color="orange")
                stat_card("ARCHITECTURE", data.get("arch"), "dns")

            # ROW 2: WORKSPACE & SIDEBAR (Fills remaining height)
            # KEY FIX: 'no-wrap' forces side-by-side.
            with ui.row().classes("w-full gap-6 items-stretch flex-grow h-full overflow-hidden no-wrap"):
                # ====================
                # KEY FIX: 'min-w-0' allows this panel to shrink if the screen gets too small, preventing overlap.
                with ui.card().classes(
                    "flex-grow w-full min-w-0 bg-white/5 border border-white/5 p-0 rounded flex flex-col"
                ):
                    # Tabs Header
                    with ui.row().classes("w-full border-b border-white/5 bg-black/20 px-2 shrink-0"):
                        tabs = (
                            ui.tabs()
                            .classes("w-full text-left")
                            .props(
                                "dense indicator-color=emerald text-color=grey-5 active-color=emerald-400 align=left narrow-indicator"  # noqa: E501 - styling
                            )
                        )

                        with tabs:
                            ui.tab("dna", label="SYSTEM IDENTITY", icon="fingerprint").classes("h-12 min-h-0")
                            ui.tab("history", label="MISSION LOG", icon="history").classes("h-12 min-h-0")
                            ui.tab("files", label="FILE SYSTEM", icon="folder").classes("h-12 min-h-0")

                    # Tabs Content
                    with ui.tab_panels(tabs, value="dna").classes(
                        "w-full flex-grow bg-transparent p-0 overflow-hidden"
                    ):
                        # PANEL 1: SYSTEM DNA
                        with ui.tab_panel("dna").classes("w-full h-full p-0"):  # noqa: SIM117
                            with ui.scroll_area().classes("w-full h-full p-4"):
                                info_row("Operating System", data.get("os_details", "N/A"))
                                info_row("Build Number", "19044.1234 (Mock)")
                                info_row("Domain", "WORKGROUP")
                                info_row("Timezone", "UTC-5 (EST)")
                                info_row("Local Admin", "True")
                                info_row("AV Status", "Defender (Active)")
                                info_row("Uptime", "14d 2h 12m")
                                info_row("Integrity Level", "Medium")

                        # PANEL 2: MISSION HISTORY
                        with ui.tab_panel("history").classes("w-full h-full p-0"):
                            with ui.column().classes("w-full h-full gap-0"):
                                # Toolbar
                                with ui.row().classes(
                                    "w-full p-2 justify-end border-b border-white/5 shrink-0 bg-black/10"
                                ):
                                    ui.button(icon="refresh", on_click=lambda: load_history()).props(
                                        "flat dense round size=xs color=grey"
                                    )

                                # Scrollable History
                                with ui.scroll_area().classes("w-full flex-grow"):
                                    history_container = ui.column().classes("w-full p-0 gap-0")

                            async def load_history():
                                history_container.clear()
                                with history_container:
                                    ui.spinner(size="lg", color="emerald-500").classes("self-center my-8 opacity-50")

                                res = await get_implant_task_history(implant_uuid)
                                tasks = res.get("data", [])
                                history_container.clear()

                                if not tasks:
                                    with history_container:
                                        ui.label("NO IMPLANT HISTORY").classes("w-full text-center tech-label-sub")
                                    return

                                with history_container:
                                    for task in reversed(tasks):
                                        render_history_row(task)

                            ui.timer(0.1, load_history, once=True)

                        # PANEL 3: FILES
                        with ui.tab_panel("files").classes(
                            "w-full h-full items-center justify-center text-neutral-600"
                        ):
                            ui.icon("folder_off", size="xl").classes("mb-2 opacity-50")
                            ui.label("FILE BROWSER MODULE NOT LOADED").classes("tech-label-sub")

                # ====================
                # KEY FIX: Strictly fixed width (w-[320px]), removed 'w-full', added 'shrink-0'
                with ui.card().classes(
                    "w-[320px] shrink-0 bg-white/5 border border-white/5 p-0 rounded shrink-0 flex flex-col"
                ):
                    # Header
                    with ui.row().classes("w-full p-3 border-b border-white/5 bg-black/20 items-center gap-2 shrink-0"):
                        ui.icon("settings", size="xs", color="emerald-500")
                        ui.label("CONTROLS //").classes("tech-label-sub")

                    # Scrollable Config
                    with ui.scroll_area().classes("w-full flex-grow"):  # noqa: SIM117
                        with ui.column().classes("p-4 w-full gap-4"):
                            # Config
                            ui.label("BEACON SETTINGS").classes("tech-label-sub")
                            with ui.row().classes("w-full gap-2"):
                                ui.input("SLEEP (s)", value=str(data.get("sleep"))).props(
                                    "outlined dense dark color=emerald"
                                ).classes("flex-1 tech-input")
                                ui.input("JITTER (%)", value=str(data.get("jitter"))).props(
                                    "outlined dense dark color=emerald"
                                ).classes("flex-1 tech-input")
                            ui.button("APPLY CONFIG", icon="save").classes(
                                "w-full tech-btn-ghost border border-white/10"
                            ).props("flat dense")

                            ui.separator().classes("bg-white/5")

                            # Scripts
                            ui.label("AUTORUN SCRIPTS").classes("tech-label-sub")
                            # options for buttons in config
                            with ui.column().classes("w-full gap-2"):
                                ui.button("SOME_BUTTON", icon="lan").classes(
                                    "w-full bg-black/20 text-neutral-400 justify-start"
                                ).props("flat dense")
                                ui.button("SOME_BUTTON2", icon="key").classes(
                                    "w-full bg-black/20 text-neutral-400 justify-start"
                                ).props("flat dense")

                    # Footer Actions
                    with ui.column().classes("w-full p-4 gap-2 bg-red-900/5 border-t border-white/5 shrink-0"):
                        ui.label("CRITICAL ACTIONS").classes("tech-label-sub")
                        with ui.row().classes("w-full gap-2"):
                            ui.button("KILL", icon="bolt").classes(
                                "flex-1 bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20"
                            ).props("unelevated dense")
                            ui.button("EXIT", icon="logout").classes(
                                "flex-1 bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20"
                            ).props("unelevated dense")


def render_history_row(task: dict):
    """Renders a single history item row"""
    task_req = task.get("task_request", {}) or {}
    task_res = task.get("task_response", {}) or {}

    task_name = task_req.get("task", {}).get("task_name", "UNKNOWN")
    task_args = task_req.get("task", {}).get("args", {})
    task_out = task_res.get("data", "")
    args_str = " ".join([f"{k}={v}" for k, v in task_args.items()])

    is_complete = bool(task_out)
    status_color = "emerald" if is_complete else "orange"
    status_icon = "check_circle" if is_complete else "pending"

    with ui.expansion().classes("w-full border-b border-white/5 group bg-transparent") as expansion:
        with expansion.add_slot("header"), ui.row().classes("w-full items-center py-2 px-1 gap-4"):
            ui.icon(status_icon, color=status_color).classes("text-lg opacity-80")
            with ui.column().classes("gap-0 flex-grow"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(task_name.upper()).classes("tech-label-sub")
                    if args_str:
                        ui.label(args_str).classes("tech-label-sub")
                ui.label(f"ID: {task.get('task_uuid', '')}").classes("tech-label-sub")

        with ui.column().classes("w-full bg-black/40 p-4 border-t border-white/5 shadow-inner"):
            ui.label("OUTPUT STREAM //").classes("tech-label-sub")
            if task_out:
                ui.code(task_out).classes(
                    "w-full bg-transparent text-emerald-400 font-mono text-xs overflow-x-auto p-0"
                )
            else:
                ui.label("Awaiting agent response...").classes("tech-label-sub")
