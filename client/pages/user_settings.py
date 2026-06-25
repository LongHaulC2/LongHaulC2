import logging

from nicegui import app, ui

from client.pages.menu import setup_menu
from client.utils.helpers import notify

server_log = logging.getLogger("server")


def initialize_default_settings() -> None:
    """Populate the user storage with default application settings."""
    defaults = {
        "auto_refresh_rate": 1,
        "notification_position": "bottom",
    }

    for key, value in defaults.items():
        if key not in app.storage.user:
            app.storage.user[key] = value


@ui.page("/settings")
async def settings_page() -> None:
    """Configure the layout and initialize the user settings page."""
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Preferences")

    initialize_default_settings()
    await settings_view()


async def settings_view() -> None:
    """Render the main UI components for the settings interface."""
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel bg-[#0a0a0a]"):
        # Header section
        with (
            ui.row().classes(
                "w-full items-center justify-between tech-header-bar p-4 border-b border-white/5 bg-[#0f0f0f]"
            ),
            ui.row().classes("items-center gap-3"),
        ):
            ui.icon("tune", color="emerald-500").classes("text-xl")
            ui.label("USER SETTINGS //").classes("tech-label-sub")

        # Main scrollable settings container
        with ui.scroll_area().classes("w-full flex-grow p-8"):  # noqa: SIM117 - nicegui, mutliple with's are fine
            with ui.column().classes("w-full max-w-4xl mx-auto gap-8 pb-20"):
                ui.label("All values here auto-save on change").classes("tech-header-bar w-full text-center")
                # System & Telemetry Section
                with ui.column().classes("w-full gap-4 mt-4"):
                    with ui.row().classes("w-full items-center gap-2 border-b border-white/10 pb-2"):
                        ui.icon("memory", color="neutral-500").classes("text-sm")
                        ui.label("Settings").classes("tech-label-sub")

                    with ui.row().classes("w-full gap-8 items-start bg-white/5 p-4 rounded border border-white/5"):
                        # Refresh rate input
                        with ui.column().classes("w-1/3 gap-1"):
                            ui.label("Element Auto Refresh Rate").classes(
                                "tech-label-header-section underline font-bold"
                            )

                            ui.number(value=1, min=1, step=1, format="%.0f").bind_value(
                                app.storage.user, "auto_refresh_rate"
                            ).props("outlined dense dark color=emerald").classes("tech-label-sub w-32 my-1")

                            ui.label("Lower values increase server load but provide more frequent updates.").classes(
                                "tech-label-sub opacity-70"
                            )

                        # Affected components list
                        with ui.column().classes("flex-grow gap-1 border-l border-white/10 pl-6"):
                            ui.label("Affects").classes("tech-label-sub font-bold mb-1")
                            ui.separator()

                            with ui.column().classes("gap-2 pl-2"):
                                affected_components = [
                                    "Operations: Terminal update interval",
                                    "Operations: Implant Table update interval",
                                    "Footer: Update interval",
                                    "Graph: Update interval",
                                ]
                                for component in affected_components:
                                    with ui.row().classes("items-center gap-2"):
                                        ui.icon("circle", size="6px", color="emerald")
                                        ui.label(component).classes("tech-label-sub")

                    # Notification position card
                    with (  # noqa: SIM117 - nicegui, multiple with's are fine
                        ui.row().classes("w-full gap-8 items-start bg-white/5 p-4 rounded border border-white/5"),
                        ui.column().classes("w-1/3 gap-1"),
                    ):
                        ui.label("Notification Position").classes("tech-label-header-section underline font-bold")

                        ui.select(
                            options=[
                                "top-left",
                                "top-right",
                                "top",
                                "bottom-left",
                                "bottom-right",
                                "bottom",
                                "left",
                                "right",
                                "center",
                            ],
                            value="bottom",
                        ).bind_value(app.storage.user, "notification_position").props(
                            "outlined dense dark color=emerald"
                        ).classes("tech-label-sub w-40 my-1")

                        ui.label("Where notifications appear on screen.").classes("tech-label-sub opacity-70")

                # Danger Zone Section
                with ui.column().classes("w-full gap-4 mt-8"):
                    with ui.row().classes("w-full items-center gap-2 border-b border-red-500/20 pb-2"):
                        ui.icon("warning", color="red-500").classes("text-sm")
                        ui.label("WARNING").classes(
                            "text-xs font-mono text-red-500 tracking-widest font-bold uppercase"
                        )

                    with ui.row().classes(
                        "w-full justify-between items-center bg-red-900/10 p-4 rounded border border-red-500/20"
                    ):
                        with ui.column().classes("gap-0"):
                            ui.label("RESET SETTINGS").classes("tech-label-header-section underline")
                            ui.label("Revert all settings to system defaults. This action cannot be undone.").classes(
                                "tech-label-sub"
                            )
                            ui.label(
                                "You will be logged out, as this clears all user settings, including your active token"
                            ).classes("tech-label-sub")

                        def trigger_reset() -> None:
                            """Clear user storage and reload the page to apply defaults."""
                            app.storage.user.clear()
                            initialize_default_settings()
                            notify("PREFERENCES RESET TO DEFAULT", type="warning", color="red-9")
                            ui.navigate.to("/settings")

                        ui.button("RESET TO DEFAULT", on_click=trigger_reset).props("outline dense color=red").classes(
                            "font-mono text-xs font-bold tracking-wider"
                        )
