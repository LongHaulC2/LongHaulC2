from nicegui import app, ui

from client.pages.formatted_tooltip import formatted_tooltip


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


async def back_button():
    """Standard back button that navigates to previous URI from tab storage."""
    await ui.context.client.connected()
    prev_uri = app.storage.tab.get("previous_uri", "/")
    with (
        ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to(prev_uri))
        .props("flat dense square size=sm")
        .classes("tech-btn-ghost")
    ):
        formatted_tooltip(prev_uri)
