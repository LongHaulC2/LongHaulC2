from nicegui import ui


def setup_menu():
    with ui.header().classes(replace="row items-center") as header:
        ui.button(on_click=lambda: left_drawer.toggle(), icon="menu").props(
            "flat color=white"
        )
        ui.label("SomeTExt?")
        # with ui.tabs() as tabs:
        #     ui.tab("A")
        #     ui.tab("B")
        #     ui.tab("C")

    with ui.left_drawer(elevated=False, bordered=False).classes(
        "bg-grey-100"
    ) as left_drawer:
        ui.label("Side menu").classes("px-4 py-2 text-grey-700 font-semibold")

        ui.button(
            "Operations",
            icon="build",
        ).classes(
            "w-full justify-start px-4"
        ).props(" no-caps flat")

        ui.button(
            "[placeholder] Help",
            icon="help_outline",
        ).classes(
            "w-full justify-start px-4"
        ).props("no-caps flat")

        ui.button(
            "[placeholder] Settings",
            icon="settings",
        ).classes(
            "w-full justify-start px-4"
        ).props("no-caps flat")

    # with ui.tab_panels(tabs, value="A").classes("w-full"):
    #     with ui.tab_panel("A"):
    #         ui.label("Content of A")
    #     with ui.tab_panel("B"):
    #         ui.label("Content of B")
    #     with ui.tab_panel("C"):
    #         ui.label("Content of C")
