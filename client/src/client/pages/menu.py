from nicegui import ui

from client.src.client.style import *

from ..utils.checks import check_type


def setup_menu(title: str):
    check_type(title, str, "title")
    left_drawer = ui.left_drawer(value=False, elevated=False, bordered=False).classes(
        "bg-grey-100"
    )
    with ui.header().classes(
        add=f"{NAVBAR_COLOR}", replace="row items-center"
    ) as header:
        ui.button(on_click=lambda: left_drawer.toggle(), icon="menu").props(
            "flat color=white"
        )

        ui.label(title)

    # value=false keeps the drawer closed by default
    with left_drawer:
        # ui.label("Side menu").classes("px-4 py-2 text-emerald-100 font-semibold")

        ui.button(
            "Operations", icon="build", on_click=lambda: ui.navigate.to("/operations")
        ).classes("w-full px-4 text-white").props("flat no-caps")

        ui.button(
            "Payloads",
            icon="outbound",
            on_click=lambda: ui.navigate.to("/payloads"),
        ).classes("w-full px-4 text-white").props("flat no-caps")

        ui.button(
            "Listeners",
            icon="headphones",
            on_click=lambda: ui.navigate.to("/listeners"),
        ).classes("w-full px-4 text-white").props("flat no-caps")

        ui.button(
            "Search", icon="search", on_click=lambda: ui.navigate.to("/search")
        ).classes("w-full px-4 text-white").props("flat no-caps")

        ui.button(
            "Scripts", icon="code", on_click=lambda: ui.navigate.to("/scripts")
        ).classes("w-full px-4 text-white").props("flat no-caps")

        # Version label at the bottom
        with ui.row().classes("mt-auto w-full"):
            ui.separator().classes("w-full")
            ui.label("Version Beta ?.0.0").classes(
                "w-full text-sm text-center text-gray-500 mt-auto px-4 py-2"
            )
