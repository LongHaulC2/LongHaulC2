from nicegui import ui
from client.src.client.style import *


def setup_menu():
    left_drawer = ui.left_drawer(value=False, elevated=False, bordered=False).classes(
        "bg-grey-100"
    )
    with ui.header().classes(
        add=f"{NAVBAR_COLOR}", replace="row items-center"
    ) as header:
        ui.button(on_click=lambda: left_drawer.toggle(), icon="menu").props(
            "flat color=white"
        )

    # value=false keeps the drawer closed by default
    with left_drawer:
        ui.label("Side menu").classes("px-4 py-2 text-emerald-100 font-semibold")

        ui.button(
            "Operations", icon="build", on_click=lambda: ui.navigate.to("/operations")
        ).classes("w-full justify-start text-left px-4 text-white").props(
            "flat no-caps"
        )

        ui.button(
            "[placeholder] Help",
            icon="help_outline",
        ).classes(
            "w-full justify-start text-left px-4 text-white"
        ).props("flat no-caps")

        ui.button(
            "[placeholder] Settings",
            icon="settings",
        ).classes(
            "w-full justify-start text-left px-4 text-white"
        ).props("flat no-caps ")
