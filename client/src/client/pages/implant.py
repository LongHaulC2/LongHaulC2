import json

import structlog
from nicegui import ui

from client.src.client.modules.api_calls import get_implant_data, get_implant_task_history
from client.src.client.pages.footer import build_footer
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


def render_history_row(task: dict):
    """Renders a single history item row flat against the bg"""
    task_req = task.get("task_request", {}) or {}
    task_res = task.get("task_response", {}) or {}

    task_name = task_req.get("task", {}).get("task_name", "UNKNOWN")
    task_args = task_req.get("task", {}).get("args", {})
    task_out = task_res.get("implant_metadata", "")
    args_str = " ".join([f"{k}={v}" for k, v in task_args.items()])

    is_complete = bool(task_out)
    status_color = "emerald" if is_complete else "amber"
    status_icon = "check_circle" if is_complete else "pending"

    # Flat expansion row
    with ui.expansion().classes("w-full border-b border-white/5 bg-transparent group") as expansion:
        with expansion.add_slot("header"), ui.row().classes("w-full items-center py-1 gap-4 flex-nowrap"):
            ui.icon(status_icon, color=status_color).classes("text-sm opacity-80 shrink-0")
            with ui.column().classes("gap-0 flex-grow"):
                with ui.row().classes("items-baseline gap-2"):
                    ui.label(task_name).classes("text-xs font-mono font-bold text-white")
                    if args_str:
                        ui.label(args_str).classes("text-[10px] font-mono text-neutral-400 truncate max-w-md")
                ui.label(f"ID: {task.get('task_uuid', '')}").classes("tech-label-sub")

        # --- Request Section ---
        with ui.column().classes("w-full bg-black/40 p-4 border-t border-white/5 shadow-inner"):
            ui.label("REQUEST DATA //").classes("text-[10px] text-emerald-500/50 font-mono mb-1")
            # Using json.dumps for pretty printing
            ui.code(json.dumps(task_req, indent=2)).classes(
                "w-full bg-transparent text-emerald-400 font-mono text-xs overflow-x-auto p-0 m-0"
            )

        # --- Response Section ---
        with ui.column().classes("w-full bg-black/40 p-4 border-t border-white/5 shadow-inner"):
            ui.label("RESPONSE DATA //").classes("text-[10px] text-emerald-500/50 font-mono mb-1")
            if task_res:
                # Using json.dumps for pretty printing
                ui.code(json.dumps(task_res, indent=2)).classes(
                    "w-full bg-transparent text-emerald-400 font-mono text-xs overflow-x-auto p-0 m-0"
                )
            else:
                ui.label("No Response").classes("text-[12px] font-mono text-neutral-500 italic")


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

    setup_menu("Implant View")

    # Fetch Implant Metaimplant_metadata
    api_res = await get_implant_data(implant_uuid)
    implant_metadata = api_res.get("data", {}) or {}

    # Render Dashboard
    await render_dashboard(implant_metadata, implant_uuid)
    await build_footer()


# ========================================
# dashboard
# ========================================
async def render_dashboard(implant_metadata: dict, implant_uuid: str):
    hostname = implant_metadata.get("system_hostname", "?")
    user = implant_metadata.get("user", "UNKNOWN")
    process_name = implant_metadata.get("process", "?")

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
                    ui.label(f"{user} @ {hostname}").classes(
                        "text-sm font-bold tracking-[0.2em] text-white font-mono uppercase"
                    )
                    ui.label(f"IMPLANT_UUID // {implant_uuid}").classes(
                        "text-[12px] font-mono text-emerald-500 tracking-[0.2em]"
                    )

            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "INTERACT",
                    icon="terminal",
                    on_click=lambda: ui.navigate.to("/operations"),
                ).classes("!tech-btn-action px-4").props("unelevated dense")

        # ====================
        #   2. VITALS BAR (Flat layout replacing stat_cards)
        # ====================
        with ui.row().classes(
            "w-full h-10 gap-0 bg-black/20 border-b border-white/5 items-center shrink-0 flex-nowrap overflow-x-auto"
        ):
            flat_stat("USER", user, "person", "emerald")
            flat_stat("EXT NETWORK ADDR", implant_metadata.get("external_ip", "0.0.0.0"), "lan", "blue")
            flat_stat(
                "PROCESS",
                process_name,
                "memory",
                "purple",
            )
            flat_stat("LAST SEEN", str(implant_metadata.get("last_seen", "Unknown")), "schedule", "orange")
            flat_stat("ARCH", implant_metadata.get("arch", "x64"), "dns", "grey")

        # ====================
        #   3. BODY
        # ====================
        with ui.row().classes("w-full flex-grow p-4 gap-4 overflow-hidden no-wrap items-stretch"):  # noqa - nicegui styling
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
                        ui.tab("metadata_tab", label="METADATA").classes("h-10 min-h-0 tech-label-sub")
                        ui.tab("history_tab", label="COMMAND HISTORY").classes("h-10 min-h-0 tech-label-sub")
                        # ui.tab("graph_tab", label="GRAPH").classes("h-10 min-h-0 tech-label-sub")
                        ui.tab("terminal_tab", label="TERMINAL").classes("h-10 min-h-0 tech-label-sub")

                # Tabs Content
                with ui.tab_panels(tabs, value="metadata_tab").classes("w-full flex-grow bg-transparent p-0"):
                    # Metadata Tab
                    with ui.tab_panel("metadata_tab").classes("w-full h-full p-0"):  # noqa
                        with ui.scroll_area().classes("w-full h-full p-4"):
                            for key, value in implant_metadata.items():
                                info_row(key, value)

                    # Command History Tab
                    with ui.tab_panel("history_tab").classes("w-full h-full p-0"):  # noqa
                        with ui.column().classes("w-full h-full gap-0"):
                            with ui.row().classes(
                                "w-full p-2 justify-end border-b border-white/5 shrink-0 bg-black/20"
                            ):
                                ui.button(icon="refresh", on_click=lambda: load_history()).props(
                                    "flat dense square size=xs color=grey"
                                )

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
                                        ui.label("NO IMPLANT HISTORY").classes("w-full text-center tech-label-sub my-8")
                                    return

                                with history_container:
                                    for task in reversed(tasks):
                                        render_history_row(task)

                            ui.timer(0.1, load_history, once=True)

                    # Graph Tab
                    # with ui.tab_panel("graph_tab").classes(
                    #     "w-full h-full items-center justify-center text-neutral-600"
                    # ):
                    #     ui.icon("hub", size="xl").classes("mb-2 opacity-50")
                    #     ui.label("GRAPH MODULE NOT IMPLEMENTED").classes("tech-label-sub")

                    # Terminal Tab
                    with ui.tab_panel("terminal_tab").classes(
                        "w-full h-full items-center justify-center text-neutral-600"
                    ):
                        ui.icon("terminal", size="xl").classes("mb-2 opacity-50")
                        ui.label("TERMINAL MODULE NOT IMPLEMENTED").classes("tech-label-sub")

                # Footer Actions
                with ui.column().classes("w-full p-4 gap-2 border-t  shrink-0"):
                    ui.label("ACTIONS").classes("tech-label-sub ")
                    # with ui.row().classes("w-full gap-2"):
                    # ui.button("KILL", icon="bolt").classes(
                    #     "flex-1 bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20 transition-colors"  # noqa
                    # ).props("unelevated dense")
                    # ui.button("EXIT", icon="logout").classes(
                    #     "!tech-btn-action w-full"  # noqa
                    # ).props("unelevated dense")
