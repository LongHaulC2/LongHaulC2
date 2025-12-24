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
        ui.label("Implants")
        with ui.button(icon="terminal", on_click=lambda: ...).props("dense flat round"):
            ui.tooltip("Open shell")  # with ui.tabs() as tabs:
        #     ui.tab("A")
        #     ui.tab("B")
        #     ui.tab("C")

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

    # with ui.tab_panels(tabs, value="A").classes("w-full"):
    #     with ui.tab_panel("A"):
    #         ui.label("Content of A")
    #     with ui.tab_panel("B"):
    #         ui.label("Content of B")
    #     with ui.tab_panel("C"):
    #         ui.label("Content of C")
