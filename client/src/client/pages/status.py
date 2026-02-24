import logging

from nicegui import ui

from client.src.client.modules.api_calls import (
    get_all_listener_data,
    get_health_status,
    restart_listener,
    start_listener_from_existing,
    stop_listener,
)

# Imports
from client.src.client.pages.menu import setup_menu

server_log = logging.getLogger("server")


async def fetch_system_status() -> dict:
    """Get data from API"""

    data = await get_health_status()
    data = data.get("data")  # pull out from api struct
    return data


# ==============================================================================
# UTILITIES
# ==============================================================================
def parse_status(raw_status: str):
    """Parses backend status strings into UI context (text, color, icon)."""
    raw_status = str(raw_status).lower().strip()

    if raw_status.startswith("running"):
        return "RUNNING", "emerald", "check_circle"

    elif raw_status.startswith("stopped"):
        # Extract exit code if present, e.g., "stopped(-15)" -> "-15"
        details = raw_status.replace("stopped", "").strip("()")
        label = f"STOPPED [{details}]" if details else "STOPPED"
        # Red for error codes, Amber for clean stops (0 or blank)
        color = "red" if details and details != "0" else "amber"
        return label, color, "cancel"

    else:
        return raw_status.upper(), "grey", "help"


# ==============================================================================
# PAGE LOGIC
# ==============================================================================


@ui.page("/status")
async def status_page():
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("System Status")

    # --- INTERNAL DOM REGISTRY ---
    # We store references to the UI elements here so we can update them in-place
    ui_registry = {"core": {}, "listeners": {}}

    app_state = {"auto_refresh": True}

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel bg-[#0a0a0a]"):
        # --- HEADER BAR ---
        with ui.row().classes(
            "w-full items-center justify-between tech-header-bar p-4 border-b border-white/5 bg-[#0f0f0f]"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("monitor_heart", color="emerald-500").classes("text-xl animate-pulse")
                ui.label("SYSTEM_TELEMETRY //").classes("text-sm font-bold tracking-[0.2em] text-white font-mono")

            with ui.row().classes("items-center gap-4"):
                # Auto-refresh toggle
                status_label = ui.label("AUTO-REFRESH: ON").classes(
                    "text-[10px] font-mono tracking-widest text-emerald-500"
                )

                def toggle_refresh(e):
                    app_state["auto_refresh"] = e.value
                    if e.value:
                        status_label.set_text("AUTO-REFRESH: ON")
                        status_label.classes(replace="text-[10px] font-mono tracking-widest text-emerald-500")
                    else:
                        status_label.set_text("AUTO-REFRESH: OFF")
                        status_label.classes(replace="text-[10px] font-mono tracking-widest text-red-500")

                ui.switch(value=True, on_change=toggle_refresh).props("dark color=emerald size=sm")

        with ui.scroll_area().classes("w-full flex-grow p-6"):
            with ui.row().classes("w-full items-start gap-8 flex-nowrap"):
                # Column 1: Core
                with ui.column().classes("w-1/2 gap-4"):
                    ui.label("CORE_SERVICES").classes(
                        "text-xs font-mono text-neutral-500 tracking-widest font-bold border-b border-white/10 w-full "
                        "pb-2"
                    )
                    core_container = ui.column().classes("w-full gap-2")

                # Column 2: Listeners
                with ui.column().classes("w-1/2 gap-4"):
                    ui.label("LISTENER_PROCESSES").classes(
                        "text-xs font-mono text-neutral-500 tracking-widest font-bold border-b border-white/10 w-full "
                        "pb-2"
                    )
                    listener_container = ui.column().classes("w-full gap-2")

    async def handle_action(category: str, svc_name: str, action: str):
        """
        Dispatches Start/Stop/Restart commands to the backend.
        svc_name corresponds to the listener_uuid in this context.
        """
        if category == "listeners":
            try:
                # correlate listener name -> uuid (because the API does not return the UUID... yay)
                listeners_data = await get_all_listener_data()
                listeners_data = listeners_data.get("data", {})

                # create a quick mapping of "name":"uuid" to avoid looping
                name_to_uuid = {
                    listener.get("listener_name"): listener.get("listener_uuid") for listener in listeners_data
                }
                listener_uuid = name_to_uuid.get(svc_name, "")

                if action == "start":
                    # Assuming svc_name is your listener_uuid
                    await start_listener_from_existing(listener_uuid)
                    # ui.notify(f"Started listener: {svc_name}", type="positive")

                elif action == "stop":
                    await stop_listener(listener_uuid)
                    # ui.notify(f"Stopped listener: {svc_name}", type="negative")

                elif action == "restart":
                    await restart_listener(listener_uuid)
                    # notify  only on restart, as this doesn't trigger the health watchdog
                    ui.notify(f"Restarted listener: {svc_name}", type="info")

                # Trigger an immediate refresh of the UI data
                await poll_data()

            except Exception as e:
                ui.notify(f"Action failed: {str(e)}", type="warning")
        else:
            # logic for core services when I want to implement that handling
            ui.notify(f"Action {action} not implemented for Core services", color="grey")

    def build_service_row(container, category: str, svc_name: str, initial_raw_status: str):
        """Draws a service row for the first time and registers its UI components."""
        text, color, icon_name = parse_status(initial_raw_status)

        with container:
            row_box = ui.row().classes(
                f"w-full items-center justify-between p-3 rounded border border-{color}-500/20 bg-{color}-900/10 "
                "transition-colors duration-300"
            )

            with row_box:
                # Info Side
                with ui.row().classes("items-center gap-3"):
                    status_icon = ui.icon(icon_name, color=f"{color}-500").classes("transition-colors duration-300")
                    with ui.column().classes("gap-0"):
                        ui.label(svc_name.upper()).classes("text-xs font-bold font-mono text-white")
                        status_text = ui.label(text).classes(
                            f"text-[10px] font-mono text-{color}-400 font-bold tracking-widest transition-colors "
                            "duration-300"
                        )

                # Controls Side
                with ui.row().classes("gap-1"):
                    btn_start = (
                        ui.button(icon="play_arrow", on_click=lambda: handle_action(category, svc_name, "start"))
                        .props("dense flat size=sm color=emerald-400")
                        .tooltip("Start")
                    )
                    btn_restart = (
                        ui.button(icon="restart_alt", on_click=lambda: handle_action(category, svc_name, "restart"))
                        .props("dense flat size=sm color=blue-400")
                        .tooltip("Restart")
                    )
                    btn_stop = (
                        ui.button(icon="stop", on_click=lambda: handle_action(category, svc_name, "stop"))
                        .props("dense flat size=sm color=red-400")
                        .tooltip("Stop")
                    )

        # Save to registry for fast updates later
        ui_registry[category][svc_name] = {
            "raw_status": initial_raw_status,
            "row_box": row_box,
            "status_icon": status_icon,
            "status_text": status_text,
            "btn_start": btn_start,
            "btn_restart": btn_restart,
            "btn_stop": btn_stop,
        }

    def update_service_row(category: str, svc_name: str, new_raw_status: str):
        """Updates an existing row's text and colors in-place if the status changed."""
        registry_entry = ui_registry[category][svc_name]

        if registry_entry["raw_status"] == new_raw_status:
            return  # No change, skip DOM updates

        # Parse new state
        text, color, icon_name = parse_status(new_raw_status)

        # Update UI Elements in-place
        registry_entry["status_text"].set_text(text)
        registry_entry["status_text"].classes(
            replace=f"text-[10px] font-mono text-{color}-400 font-bold tracking-widest transition-colors duration-300"
        )

        registry_entry["status_icon"].name = icon_name
        registry_entry["status_icon"].props(f"color={color}-500")

        registry_entry["row_box"].classes(
            replace=f"w-full items-center justify-between p-3 rounded border border-{color}-500/20 bg-{color}-900/10 "
            "transition-colors duration-300"
        )

        # Toggle button visibility based on state
        is_running = "running" in new_raw_status.lower()
        registry_entry["btn_start"].set_visibility(not is_running)
        registry_entry["btn_restart"].set_visibility(is_running)
        registry_entry["btn_stop"].set_visibility(is_running)

        # Save new state
        registry_entry["raw_status"] = new_raw_status

    async def poll_data():
        """Timer callback. Fetches data and mutates the DOM via the registry."""
        if not app_state["auto_refresh"]:
            return

        try:
            data_response = await fetch_system_status()
        except Exception as e:
            server_log.error(f"Failed telemetry pull: {e}")
            return

        # Process Core
        for svc_name, status in data_response.get("core", {}).items():
            if svc_name not in ui_registry["core"]:
                build_service_row(core_container, "core", svc_name, status)
                # Ensure buttons are set correctly on first draw
                update_service_row("core", svc_name, status)
            else:
                update_service_row("core", svc_name, status)

        # Process Listeners
        for svc_name, status in data_response.get("listeners", {}).items():
            if svc_name not in ui_registry["listeners"]:
                build_service_row(listener_container, "listeners", svc_name, status)
                update_service_row("listeners", svc_name, status)
            else:
                update_service_row("listeners", svc_name, status)

    # Fire the loop every 1.0 seconds
    ui.timer(1.0, poll_data)
