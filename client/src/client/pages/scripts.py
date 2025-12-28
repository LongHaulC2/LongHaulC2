import httpx
from nicegui import ui, events
import logging
from client.src.client.pages.menu import setup_menu
from client.src.client.utils.url import generate_url
from typing import Optional
from pathlib import Path
import asyncio
import sys

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

    # ui.query(".nicegui-content").classes("p-0 gap-0")

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
                        await terminal_setup()


# -------------------------------
# Terminal
# -------------------------------
# global tabs for being able to access tab functions & vars without doing some weirder stuff
# TLDR: nicegui & async don't play nice with classes, it's much cleaner to use globals like this.
terminal_tabs_parent = None
terminal_panels_parent = None
terminal_open_tabs = {}


async def terminal_setup():
    global terminal_tabs_parent, terminal_panels_parent

    # init tabs and panel view (basically just a container that exists)
    # width/height full set here
    terminal_tabs_parent = ui.tabs().props("dense indicator-color=grey")
    terminal_panels_parent = (
        ui.tab_panels(terminal_tabs_parent).classes("w-full h-full")
        # transition is set to 0, this disables the nauseating "panel slide"
        .props("dense transition-duration=0")
    )


async def terminal_add_tab(tab_name):
    """
    tab_name: Name of tab to add to the Terminal tab space
    """
    global terminal_tabs_parent, terminal_panels_parent, terminal_open_tabs

    # already open == switch
    if tab_name in terminal_open_tabs:
        terminal_panels_parent.set_value(tab_name)
        ui.notify("Tab already open")
        return

    # create tab
    with terminal_tabs_parent:
        with ui.tab(tab_name, label="").classes("p-0 rounded-none") as tab:
            tab.meta = {"tab_name": tab_name}

            # tab header with label and close button
            with ui.row().classes("items-center gap-0"):
                ui.label(tab_name).classes("px-3 py-1 text-sm border-l")
                ui.button(
                    "✕", on_click=lambda tn=tab_name: terminal_close_tab(tn)
                ).props("flat dense").classes(
                    "w-6 h-full px-0 text-xs rounded-none border-r"
                )

    # create panel
    with terminal_panels_parent:
        with ui.tab_panel(tab_name) as panel:
            # create terminal
            terminal_log = ui.log().classes("w-full h-full outline")

    # Store both objects in the open tabs dict
    terminal_open_tabs[tab_name] = {
        "tab_object": tab,
        "panel_object": panel,
        "log_object": terminal_log,  # <-- store it here
    }

    # switch to new tab
    terminal_panels_parent.set_value(tab_name)


async def terminal_close_tab(tab_name):
    """
    tab_name: Name of tab to remove from the terminal tab space
    """
    global terminal_tabs_parent, terminal_panels_parent, terminal_open_tabs

    if tab_name not in ide_open_tabs:
        ui.notify(f"Tab {tab_name} not found")
        return

    # Remove the tab from the tabs object
    tab_object = terminal_open_tabs[tab_name]["tab_object"]
    terminal_tabs_parent.remove(tab_object)

    # Remove the tab panel content & from dict
    tab_panel = terminal_open_tabs[tab_name].get("panel_object")
    if tab_panel:
        terminal_panels_parent.remove(tab_panel)
    terminal_open_tabs.pop(tab_name)

    # If no tabs left, clear editor area or add aplaceholder when everything is closed
    if not ide_open_tabs:
        ...
        # with ide_panels_parent:
        # ui.label("No tabs open").classes("text-center text-grey")


# not super robust, could break fairly easily
# async def open_tab_and_execute_script(tab_name: str, script_path: str):
#     python_path = sys.executable

#     proc = await asyncio.create_subprocess_exec(
#         python_path,
#         script_path,
#         stdout=asyncio.subprocess.PIPE,
#         stderr=asyncio.subprocess.PIPE,
#         # text=True,
#     )

#     terminal_log = terminal_open_tabs[tab_name].get("log_object")

#     terminal_log.push(f"[Script: {script_path}]")
#     terminal_log.push(f"[Interpreter: {python_path}]")
#     terminal_log.push(f"[PID: {proc.pid}]")
#     terminal_log.push(
#         f"[Warning: Need shutdown/crash handling to kill all PID's at exit]"
#     )

#     # Read stdout asynchronously line by line
#     async for line in proc.stdout:
#         terminal_log.push(line.strip())

#     # Read stderr asynchronously line by line
#     async for line in proc.stderr:
#         terminal_log.push(line.strip())

#     await proc.wait()
#     terminal_log.push(f"[Process {proc.pid} finished]")


async def open_tab_and_execute_script(tab_name: str, script_path: str):
    """
    Executes a python script & spawns a new terminal for it to run in,
    streaming stdout and stderr asynchronously to the terminal log.
    """
    await terminal_add_tab(tab_name)

    terminal_log = terminal_open_tabs[tab_name].get("log_object")
    python_path = sys.executable

    # Launch the script as a new subprocess asynchronously
    proc = await asyncio.create_subprocess_exec(
        python_path,
        "-u",  # need to run pyhton in unbuffered mode, otherwse stdout waits till crash/script end for output.
        script_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        # text=True,
    )

    # Store the process in the tab dict for later cleanup [not implemented yet]
    terminal_open_tabs[tab_name]["process"] = proc

    terminal_log.push(f"[Script: {script_path}]")
    terminal_log.push(f"[Interpreter: {python_path}]")
    terminal_log.push(f"[PID: {proc.pid}]")
    terminal_log.push(
        "[Warning: Need shutdown/crash handling to kill all PID's at exit]"
    )
    terminal_log.push("[Warning: BUSTED ON WINDOWS DUE TO ASYNC LOOP THING.]")

    # Read stdout and stderr line by line asynchronously
    async def stream_output(stream, log):
        async for line in stream:
            terminal_log.push(line.strip())

    await asyncio.gather(
        stream_output(proc.stdout, terminal_log),
        stream_output(proc.stderr, terminal_log),
    )

    # Wait for process to finish
    await proc.wait()
    terminal_log.push(f"[Process {proc.pid} finished]")


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
            ).classes(f"w-full").props("dense flat square")

    async def open_code_file(file_name, file_path):
        await ide_add_tab(tab_name=file_name, script_path=file_path)


# -------------------------------
# IDE
# -------------------------------
# global tabs for being able to access tab functions & vars without doing some weirder stuff
# TLDR: nicegui & async don't play nice with classes, it's much cleaner to use globals like this.
ide_tabs_parent = None
ide_panels_parent = None
ide_open_tabs = {}


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


async def code_editor(file_path: str, script_output_terminal_tab_name: str):
    with open(file_path, "r+") as file:
        file_contents = file.read()

    # spacing is quite large, see if possibel to cut down, or move somewhere else
    with ui.row().classes("w-full justify-end q-gutter-xs"):
        with ui.button(
            icon="play_arrow",
            on_click=lambda: open_tab_and_execute_script(
                script_output_terminal_tab_name, script_path=file_path
            ),
        ).props("dense flat round").classes(f"[&_.q-icon]:{ICON_COLOR}"):
            ui.tooltip("Run script")

        with ui.button("IDONTWORKYET", icon="stop", on_click=lambda: ...).props(
            "dense flat round"
        ).classes(f"[&_.q-icon]:{ICON_COLOR} disabled"):
            ui.tooltip("Stop script")

    # ui.label("editor_placeholder")
    # No need for a scrolling section, it's built into the editor
    editor = ui.codemirror(
        file_contents, theme="androidstudio", language="Python"
    ).classes("h-full w-full outline p-0 gap-0")
    # print(editor.supported_themes)


# Global function to add a tab from anywhere
async def ide_add_tab(tab_name: str, script_path: str):
    """
    tab_name: Name of tab to add to the IDE tab space
    script_path: Path of the script that will be opened in the IDE tab
    """
    global ide_tabs_parent, ide_panels_parent, ide_open_tabs

    # already open == switch
    if tab_name in ide_open_tabs:
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
            # use tab name as same name for process tab.
            await code_editor(script_path, tab_name)

    # Store both objects in the open tabs dict
    ide_open_tabs[tab_name] = {
        "tab_object": tab,
        "panel_object": panel,
    }

    # switch to new tab
    ide_panels_parent.set_value(tab_name)


async def ide_close_tab(tab_name):
    """
    tab_name: Name of tab to close in the IDE tab space.
    """

    global ide_tabs_parent, ide_panels_parent, ide_open_tabs

    if tab_name not in ide_open_tabs:
        ui.notify(f"Tab {tab_name} not found")
        return

    # Remove the tab from the tabs object
    tab_object = ide_open_tabs[tab_name]["tab_object"]
    ide_tabs_parent.remove(tab_object)

    # Remove the tab panel content & from dict
    tab_panel = ide_open_tabs[tab_name].get("panel_object")
    if tab_panel:
        ide_panels_parent.remove(tab_panel)
    ide_open_tabs.pop(tab_name)

    # If no tabs left, clear editor area or add aplaceholder when everything is closed
    if not ide_open_tabs:
        ...
        # with ide_panels_parent:
        # ui.label("No tabs open").classes("text-center text-grey")
