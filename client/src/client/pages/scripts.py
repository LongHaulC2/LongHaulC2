import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import httpx
from nicegui import events, ui

from client.src.client.pages.menu import setup_menu

# from client.src.client.pages.menu import setup_menu
from client.src.client.style import (
    BUTTON_COLOR,
    HIGHLIGHT_COLOR,
    ICON_COLOR,
    NAVBAR_COLOR,
    TEXT_COLOR,
)
from client.src.client.utils.url import generate_url

from ..utils.checks import check_type

server_log = logging.getLogger("server")

server_log.info("Loading /scripts page")

# 1000 seems to be pretty smooth. Keeping for  now.
TERMINAL_MAX_LINES = 1000


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
    clear_state()

    # bug fix - on refresh, clear open tabs in dict, otherwise open tabs has stale tab data
    global terminal_open_tabs, ide_open_tabs
    terminal_open_tabs = {}
    ide_open_tabs = {}

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


# I really don't like this, but it works. Clears state of global vars declared in the module
# this is called at page load, to wipeout previous items. This prevents "repeat tab"/"tab already open" errors
# Dev Note: May need this for operations page as well.
def clear_state():
    global ide_tabs_parent, ide_panels_parent, ide_open_tabs
    global terminal_tabs_parent, terminal_panels_parent, terminal_open_tabs
    ide_tabs_parent = None
    ide_panels_parent = None
    ide_open_tabs = {}

    terminal_tabs_parent = None
    terminal_panels_parent = None
    terminal_open_tabs = {}


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


async def terminal_add_tab(tab_name: str):
    """
    tab_name: Name of tab to add to the Terminal tab space
    """
    global terminal_tabs_parent, terminal_panels_parent, terminal_open_tabs

    check_type(tab_name, str, "tab_name")

    # already open == switch
    if tab_name in terminal_open_tabs:
        terminal_panels_parent.set_value(tab_name)
        # not notifying, as upon executing, it will re-output to the same tab as it ran in last time.
        # not intended, but it works well so I'm keeping it.
        # ui.notify("Tab already open")
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
            terminal_log = ui.log(max_lines=TERMINAL_MAX_LINES).classes(
                "w-full h-full outline"
            )

    # Store both objects in the open tabs dict
    terminal_open_tabs[tab_name] = {
        "tab_object": tab,
        "panel_object": panel,
        "log_object": terminal_log,  # <-- store it here
    }

    # switch to new tab
    terminal_panels_parent.set_value(tab_name)


async def terminal_close_tab(tab_name: str):
    """
    tab_name: Name of tab to remove from the terminal tab space
    """
    global terminal_tabs_parent, terminal_panels_parent, terminal_open_tabs

    check_type(tab_name, str, "tab_name")

    try:
        tab_data = terminal_open_tabs.pop(tab_name)

        tab = tab_data["tab_object"]
        panel = tab_data["panel_object"]

        terminal_tabs_parent.remove(tab)
        terminal_panels_parent.remove(panel)

        # Optional: switch to another tab if any exist
        if terminal_open_tabs:
            next_uuid = next(iter(terminal_open_tabs))
            terminal_panels_parent.set_value(next_uuid)
        else:
            terminal_panels_parent.set_value(None)

    except Exception as e:
        server_log.error(e)


async def open_tab_and_execute_script(tab_name: str, script_path: str):
    """
    Executes a python script & spawns a new terminal for it to run in,
    streaming stdout and stderr asynchronously to the terminal log.
    """

    check_type(tab_name, str, "tab_name")
    check_type(script_path, str, "script_path")

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
    terminal_log.push(
        "[Warning: Output buffering is enabled for performance reasons. Data will be pushed to the terminal every 10 lines]"
    )
    terminal_log.push(
        f"[Warning: After {TERMINAL_MAX_LINES} lines, older data will be pushed out. For continuous output, please add logging in your scripts.]"
    )

    # Read stdout and stderr line by line asynchronously
    async def stream_output(stream, log):
        """
        Using a buffering mechanism to not pound the ui.log element, which can
        get a bit slow if hit too hard.

        10-100 lines works well

        Old method:
                # async for line in stream:
                #     terminal_log.push(line.strip())
        """

        buffer_size = 10  # lines
        buffer = []

        async for line in stream:
            # Add the line to the buffer
            buffer.append(line.decode().strip())

            # If the buffer reaches the specified size, push it to the log
            if len(buffer) >= buffer_size:
                log.push("\n".join(buffer))  # Push the buffered content
                buffer = []  # Clear the buffer

        # If there are any leftover lines in the buffer after the stream ends, push them
        if buffer:
            log.push("\n".join(buffer))

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


# allows for refresh on file creation
@ui.refreshable
async def file_picker():
    """
    parent file picker for the scripts tab.
    """
    # Resolve scripts folder
    script_path = Path(__file__).resolve().parent.parent / "scripts"
    script_path.mkdir(parents=True, exist_ok=True)

    server_log.info(f"Loading scripts from {str(script_path)}")

    with ui.row().classes("items-center w-full justify-between"):
        # Left-aligned label
        ui.label("Scripts").classes("text-xl font-semibold")

        # Right-aligned buttons
        with ui.row().classes("justify-end"):
            ui.button(
                icon="add", on_click=lambda: create_new_file_dialog(script_path)
            ).props("dense flat round").classes(f"[&_.q-icon]:{ICON_COLOR}").tooltip(
                "New script"
            )
            ui.button(icon="refresh", on_click=lambda: file_picker.refresh()).props(
                "dense flat round"
            ).classes(f"[&_.q-icon]:{ICON_COLOR}").tooltip("Refresh files list")

    ui.separator()

    # Prepare files for tree
    tree_items = [
        {
            "id": str(p),  # have to use ID here, that's wahat nicegui want
            "label": p.name,
            "children": [],  # no children since these are files
        }
        for p in script_path.glob("*")
        if p.is_file()
    ]
    # print(tree_items)

    # Callback to open file
    async def open_code_file(e):
        file_path = e.value  # ID is stored in value of event

        if not file_path:
            return

        file_name = Path(file_path).name
        await ide_add_tab(tab_name=file_name, script_path=file_path)

    # Create the tree
    ui.tree(
        nodes=tree_items,
        on_select=open_code_file,
    ).classes("w-full h-full")


async def create_new_file_dialog(scripts_path):
    """
    Dialog for new file
    """

    check_type(scripts_path, str, "scripts_path")

    with ui.dialog() as dialog, ui.card().classes("no-shadow"):
        ui.label("New Script")
        input_file_name = ui.input("Script Name")
        with ui.row().classes("items-center w-full justify-between"):
            ui.button(
                "Create",
                on_click=lambda: on_create(),
                color=BUTTON_COLOR,
            )
            ui.button("Close", on_click=lambda: on_close(), color=BUTTON_COLOR)

    dialog.open()

    async def on_create():
        await create_new_file(scripts_path, input_file_name.value)
        dialog.close()

    async def on_close():
        dialog.close()


async def create_new_file(file_path: str, file_name: str):
    """
    Creates a new file safely by preventing directory traversal.
    """
    check_type(file_path, str, "file_path")
    check_type(file_name, str, "file_name")

    # dir traversal protection
    base_path = Path(
        file_path
    ).resolve()  # Base directory to restrict to. Ex, /whatever/scripts

    # Join the file name to the base directory
    full_path = base_path / file_name

    # Ensure the full path is still inside the base directory, and no shenanigans are happening with path traversal
    if not full_path.resolve().is_relative_to(base_path):
        ui.notify("Try this instead: reddit.com/r/masterhacker")
        return

    # Proceed with file creation (e.g., open or write)
    try:
        with open(full_path, "w") as f:
            f.write("")
        print(f"File created at: {full_path}")
        file_picker.refresh()
    except Exception as e:
        print(f"Error creating file: {e}")


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
    """
    A code editor window that contains a ui.codemirror object, and other functionality for the editor


    file_path: the file to open and edit

    script_output_terminal_tab_name: The name of the terminal that will be used to run the current code in.

    """

    check_type(file_path, str, "file_path")
    check_type(script_output_terminal_tab_name, str, "script_output_terminal_tab_name")

    # with open(file_path, "r+") as file:
    #     file_contents = file.read()
    async def save_to_file():
        data = editor.value
        with open(file_path, "w") as file:
            file.write(data)

        ui.notify("File saved successfully")

    async def load_file():
        with open(file_path, "r+") as file:
            file_contents = file.read()
            return file_contents

    async def editor_update_file():
        data = await load_file()
        editor.value = data

    file_contents = await load_file()

    with ui.splitter(value=98, limits=(98, 98)).classes("w-full h-full") as splitter:
        # Left panel: editor
        with splitter.before:
            editor = ui.codemirror(
                file_contents,
                theme="androidstudio",
                language="Python",
            ).classes("h-full w-full outline m-0 p-0 gap-0 leading-none")

        # Right panel: vertical buttons
        with splitter.after:
            with ui.column().classes("h-full gap-1 justify-start items-center"):
                ui.button(
                    icon="play_arrow",
                    on_click=lambda: open_tab_and_execute_script(
                        script_output_terminal_tab_name, script_path=file_path
                    ),
                ).props("dense flat round").classes(f"[&_.q-icon]:{ICON_COLOR}")
                ui.tooltip("Run script")

                ui.button(
                    icon="stop",
                    on_click=lambda: ...,
                ).props(
                    "dense flat round"
                ).classes(f"disabled").props("color=negative")
                ui.tooltip("Stop script")

                ui.separator()

                ui.button(
                    icon="save",
                    on_click=lambda: save_to_file(),
                ).props(
                    "dense flat round"
                ).classes(f"[&_.q-icon]:{ICON_COLOR}")
                ui.tooltip("Save script")

                ui.button(
                    icon="refresh",
                    on_click=lambda: editor_update_file(),
                ).props(
                    "dense flat round"
                ).classes(f"[&_.q-icon]:{ICON_COLOR}")
                ui.tooltip("Reload script")


# Global function to add a tab from anywhere
async def ide_add_tab(tab_name: str, script_path: str):
    """
    tab_name: Name of tab to add to the IDE tab space
    script_path: Path of the script that will be opened in the IDE tab
    """
    global ide_tabs_parent, ide_panels_parent, ide_open_tabs

    check_type(tab_name, str, "tab_name")
    check_type(script_path, str, "script_path")

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


async def ide_close_tab(tab_name: str):
    """
    tab_name: Name of tab to close in the IDE tab space.
    """

    global ide_tabs_parent, ide_panels_parent, ide_open_tabs

    check_type(tab_name, str, "tab_name")

    try:
        tab_data = ide_open_tabs.pop(tab_name)

        tab = tab_data["tab_object"]
        panel = tab_data["panel_object"]

        ide_tabs_parent.remove(tab)
        ide_panels_parent.remove(panel)

        # Optional: switch to another tab if any exist
        if ide_open_tabs:
            next_uuid = next(iter(ide_open_tabs))
            ide_panels_parent.set_value(next_uuid)
        else:
            ide_panels_parent.set_value(None)

    except Exception as e:
        server_log.error(e)
