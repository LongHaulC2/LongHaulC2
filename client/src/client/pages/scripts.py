import httpx
from nicegui import ui, events
import logging
from client.src.client.pages.menu import setup_menu
from client.src.client.utils.url import generate_url
from typing import Optional
from pathlib import Path

# from client.src.client.pages.menu import setup_menu
from client.src.client.style import (
    BUTTON_COLOR,
    TEXT_COLOR,
    HIGHLIGHT_COLOR,
    NAVBAR_COLOR,
    ICON_COLOR,
)

server_log = logging.getLogger("server")

server_log.info("Loading /scripts page")


@ui.page("/scripts")
async def scripts():
    # HEY- readme: This is a hack to get the page full screen (and make h-full work). It should also allow for things like headers to fit without adjusting it manually
    # see the link below.
    # https://github.com/zauberzeug/nicegui/discussions/4049
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    ui.context.client.content.classes("h-full")

    setup_menu("Scripts")
    # fugly, but sets up the left right split, as well as a nested top/bottom for the IDE/Terminal split
    with ui.element().classes("w-full h-full"):
        with ui.splitter(value=15, limits=(0, 50)).classes(
            "w-full h-full"
        ) as vert_splitter:
            with vert_splitter.before:
                await file_picker()
            with vert_splitter.after:
                with ui.splitter(horizontal=True, value=70, limits=(0, 100)).classes(
                    "w-full h-full"
                ) as horiz_splitter:
                    with horiz_splitter.before:
                        # ui.label("RIGHT TOP").classes("w-full h-full")
                        await ide_setup()
                    with horiz_splitter.after:
                        # ui.label("TERM BOTTOM").classes("w-full h-full")
                        await terminal()


# -------------------------------
# Terminal
# -------------------------------


async def terminal():
    log = ui.log().classes("w-full h-full outline")
    log.push(
        "placeholder term - not final. hookup input and output of subprocess/thread that runs the scripts  to here"
    )


# -------------------------------
# File Picker
# -------------------------------


async def file_picker():
    ui.label("Scripts")
    ui.separator()
    # temp and probably breakable relative reference to the scripts folder.
    # effectively does ../../scripts
    # This would cause an issue if the client ever gets compiled (pyinstaller/nuitka)/this path doesn't exist.
    script_path = Path(__file__).resolve().parent.parent / "scripts"
    server_log.info(f"Loading scripts from {script_path}")
    # create parents if needed + okay if it exists
    script_path.mkdir(parents=True, exist_ok=True)

    files = [
        {
            "name": p.name,
            "path": str(p),
        }
        for p in script_path.glob("*")
        if p.is_file()
    ]

    with ui.scroll_area().classes("w-full h-full"):
        for file_dict in files:
            file_name = file_dict.get("name", "Error")
            file_path = file_dict.get("path", "Error")

            ui.button(
                text=file_name,
                on_click=lambda fn=file_name, fp=file_path: open_code_file(fn, fp),
            ).classes("w-full").props("dense flat square")

    async def open_code_file(file_name, file_path):
        await ide_add_tab(tab_name=file_name, script_path=file_path)


# -------------------------------
# IDE
# -------------------------------
# global tabs for being able to access tab functions & vars without doing some weirder stuff
ide_tabs_parent = None
ide_panels_parent = None
open_tabs = {}


async def ide_setup():
    global ide_tabs_parent, ide_panels_parent

    # init tabs and panel view (basically just a container that exists)
    # width/height full set here
    ide_tabs_parent = ui.tabs().props("dense indicator-color=grey")
    ide_panels_parent = (
        ui.tab_panels(ide_tabs_parent).classes("w-full h-full")
        # transition is set to 0, this disables the nauseating "panel slide"
        .props("dense transition-duration=0")
    )


async def code_editor(file_path):
    with open(file_path, "r+") as file:
        file_contents = file.read()

    # spacing is quite large, see if possibel to cut down
    with ui.row().classes("w-full justify-end q-gutter-xs"):
        with ui.button(icon="play_arrow", on_click=lambda: ...).props(
            "dense flat round"
        ).classes(f"[&_.q-icon]:{ICON_COLOR}"):
            ui.tooltip("Run script")

        with ui.button(icon="stop", on_click=lambda: ...).props(
            "dense flat round"
        ).classes(f"[&_.q-icon]:{ICON_COLOR}"):
            ui.tooltip("Stop script")

    # ui.label("editor_placeholder")
    # No need for a scrolling section, it's built into the editor
    editor = ui.codemirror(
        file_contents, theme="androidstudio", language="Python"
    ).classes("h-full w-full outline")
    # print(editor.supported_themes)


# Global function to add a tab from anywhere
async def ide_add_tab(tab_name, script_path):
    global ide_tabs_parent, ide_panels_parent, open_tabs

    # already open == switch
    if tab_name in open_tabs:
        ide_panels_parent.set_value(tab_name)
        ui.notify("Tab already open")
        return

    # create tab
    with ide_tabs_parent:
        with ui.tab(tab_name, label="").classes("p-0 rounded-none") as tab:
            tab.meta = {"tab_name": tab_name}

            # tab header with label and close button
            with ui.row().classes("items-center gap-0"):
                ui.label(tab_name).classes("px-3 py-1 text-sm border-l")
                ui.button("✕", on_click=lambda tn=tab_name: ide_close_tab(tn)).props(
                    "flat dense"
                ).classes("w-6 h-full px-0 text-xs rounded-none border-r")

    # create panel
    with ide_panels_parent:
        with ui.tab_panel(tab_name) as panel:
            await code_editor(script_path)

    # Store both objects in the open tabs dict
    open_tabs[tab_name] = {
        "tab_object": tab,
        "panel_object": panel,
    }

    # switch to new tab
    ide_panels_parent.set_value(tab_name)


async def ide_close_tab(tab_name):
    global ide_tabs_parent, ide_panels_parent, open_tabs

    if tab_name not in open_tabs:
        ui.notify(f"Tab {tab_name} not found")
        return

    # Remove the tab from the tabs object
    tab_object = open_tabs[tab_name]["tab_object"]
    ide_tabs_parent.remove(tab_object)

    # Remove the tab panel content & from dict
    tab_panel = open_tabs[tab_name].get("panel_object")
    if tab_panel:
        ide_panels_parent.remove(tab_panel)
    open_tabs.pop(tab_name)

    # If no tabs left, clear editor area or add aplaceholder when everything is closed
    if not open_tabs:
        with ide_panels_parent:
            ui.label("No tabs open").classes("text-center text-grey")
