import asyncio
import sys
from pathlib import Path

import structlog
from nicegui import ui

from client.src.client.pages.footer import build_footer
from client.src.client.pages.menu import setup_menu

from ..utils.checks import check_type

server_log = structlog.getLogger("server")
server_log.info("Loading /scripts page")

TERMINAL_MAX_LINES = 1000

# -------------------------------
# GLOBAL STATE MANAGEMENT
# -------------------------------
ide_tabs_parent = None
ide_panels_parent = None
ide_open_tabs = {}

terminal_tabs_parent = None
terminal_panels_parent = None
terminal_open_tabs = {}


def clear_state():
    global ide_tabs_parent, ide_panels_parent, ide_open_tabs
    global terminal_tabs_parent, terminal_panels_parent, terminal_open_tabs
    ide_tabs_parent = None
    ide_panels_parent = None
    ide_open_tabs = {}
    terminal_tabs_parent = None
    terminal_panels_parent = None
    terminal_open_tabs = {}


@ui.page("/scripts")
async def scripts():
    # Full Screen Layout Setup
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    clear_state()
    setup_menu("Scripts")
    await build_footer()
    # Main Layout (Splitter)
    # Using a container that matches the background
    with ui.element().classes("w-full h-full gap-0"):  # noqa: SIM117
        # Primary Splitter (Left: Files, Right: IDE/Term)
        # separator-class: Makes the divider a subtle thin line
        with ui.splitter(value=15, limits=(10, 50)).classes("w-full h-full").props(
            "separator-class=bg-white/10 separator-style=width:1px"
        ) as splitter:
            with splitter.before:
                await file_picker()

            with splitter.after:  # noqa: SIM117
                # Secondary Splitter (Top: IDE, Bottom: Terminal)
                with ui.splitter(horizontal=True, value=70, limits=(10, 90)).classes("w-full h-full").props(
                    "separator-class=bg-white/10 separator-style=height:1px"
                ) as splitter:
                    with splitter.before:
                        await ide_setup()

                    with splitter.after:
                        await terminal_setup()


# -------------------------------
# TERMINAL COMPONENT
# -------------------------------
async def terminal_setup():
    global terminal_tabs_parent, terminal_panels_parent

    # Wrapper for the bottom right panel
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel rounded-none border-0 border-t border-white/5"):
        # Header / Tabs container
        with ui.row().classes("w-full items-center bg-black/20 border-b border-white/5 px-2 h-10 gap-2"):
            ui.icon("terminal", size="xs", color="emerald-500")
            ui.label("TERMINAL_OUTPUT //").classes("tech-label-subtitle mr-4")

            # The Tabs Control
            terminal_tabs_parent = ui.tabs().props(
                "dense indicator-color=emerald text-color=grey-5 active-color=emerald-400 narrow-indicator align=left"
            )
            terminal_tabs_parent.classes("bg-transparent h-full")

        # The Panel Container
        terminal_panels_parent = (
            ui.tab_panels(terminal_tabs_parent)
            .classes("w-full h-full bg-black/40")  # Darker background for terminal area
            .props("dense transition-duration=0")
        )


async def terminal_add_tab(tab_name: str):
    global terminal_tabs_parent, terminal_panels_parent, terminal_open_tabs
    check_type(tab_name, str, "tab_name")

    if tab_name in terminal_open_tabs:
        terminal_panels_parent.set_value(tab_name)
        return

    # Create Tab Header
    with terminal_tabs_parent, ui.tab(tab_name, label="").classes("h-full px-2 min-h-0") as tab:
        tab.meta = {"tab_name": tab_name}
        with ui.row().classes("items-center gap-2"):
            ui.label(tab_name).classes("text-xs font-mono lowercase")
            ui.button(icon="close", on_click=lambda tn=tab_name: terminal_close_tab(tn)).props(
                "flat dense size=xs rounded"
            ).classes("text-neutral-500 hover:text-white")

    # Create Tab Body
    with terminal_panels_parent, ui.tab_panel(tab_name).classes("p-0 h-full w-full") as panel:
        # Terminal Log Styling
        terminal_log = ui.log(max_lines=TERMINAL_MAX_LINES).classes(
            "w-full h-full p-2 font-mono text-xs text-emerald-500/90 bg-transparent overflow-auto"
        )

    terminal_open_tabs[tab_name] = {
        "tab_object": tab,
        "panel_object": panel,
        "log_object": terminal_log,
    }
    terminal_panels_parent.set_value(tab_name)


async def terminal_close_tab(tab_name: str):
    global terminal_tabs_parent, terminal_panels_parent, terminal_open_tabs
    check_type(tab_name, str, "tab_name")
    try:
        tab_data = terminal_open_tabs.pop(tab_name)
        terminal_tabs_parent.remove(tab_data["tab_object"])
        terminal_panels_parent.remove(tab_data["panel_object"])

        if terminal_open_tabs:
            terminal_panels_parent.set_value(next(iter(terminal_open_tabs)))
        else:
            terminal_panels_parent.set_value(None)
    except Exception as e:
        server_log.error(e)


async def open_tab_and_execute_script(tab_name: str, script_path: str):
    check_type(tab_name, str, "tab_name")
    check_type(script_path, str, "script_path")

    await terminal_add_tab(tab_name)
    terminal_log = terminal_open_tabs[tab_name].get("log_object")
    python_path = sys.executable

    proc = await asyncio.create_subprocess_exec(
        python_path,
        "-u",
        script_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    terminal_open_tabs[tab_name]["process"] = proc

    # Initial Info
    terminal_log.push(f"#> {python_path} {script_path}")
    terminal_log.push(f"[SYSTEM] PID: {proc.pid} started.")

    async def stream_output(stream, log):
        buffer_size = 10
        buffer = []
        async for line in stream:
            buffer.append(line.decode().strip())
            if len(buffer) >= buffer_size:
                log.push("\n".join(buffer))
                buffer = []
        if buffer:
            log.push("\n".join(buffer))

    await asyncio.gather(
        stream_output(proc.stdout, terminal_log),
        stream_output(proc.stderr, terminal_log),
    )

    await proc.wait()
    terminal_log.push(f"[SYSTEM] Process {proc.pid} finished.")


# -------------------------------
# FILE PICKER COMPONENT
# -------------------------------
@ui.refreshable
async def file_picker():
    # hardcoded for now
    script_path = Path("/var/lib/longhaulc2")  # Path(__file__).resolve().parent.parent / "user"
    script_path.mkdir(parents=True, exist_ok=True)
    server_log.info(f"Loading scripts from {str(script_path)}")

    # Left Panel Container
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel rounded-none border-0 border-r border-white/5"):
        # Header
        with ui.row().classes("w-full items-center justify-between tech-header-bar h-12"):
            with ui.row().classes("gap-2 items-center"):
                ui.icon("folder_open", color="emerald-500")
                ui.label("SCRIPTS //").classes("tech-label-title")

            with ui.row().classes("justify-end gap-1"):
                ui.button(
                    icon="add",
                    on_click=lambda: create_new_file_dialog(str(script_path)),
                ).classes("tech-btn-action px-2").props("dense flat size=xs round").tooltip("New Script")

                ui.button(icon="refresh", on_click=lambda: file_picker.refresh()).classes("tech-btn-ghost").props(
                    "dense flat size=xs round"
                ).tooltip("Reload Tree")

        # Tree Content
        with ui.scroll_area().classes("w-full flex-grow p-2 tech-scroll"):

            def build_tree(path: Path):
                nodes = []
                for p in sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
                    node = {
                        "id": str(p),
                        "label": p.name,
                        "children": build_tree(p) if p.is_dir() else [],
                    }
                    nodes.append(node)
                return nodes

            tree_items = build_tree(script_path)

            async def open_code_file(e):
                file_path = Path(e.value)
                if not file_path.is_file():
                    return

                executable = file_path.suffix == ".py"
                await ide_add_tab(
                    tab_name=file_path.name,
                    script_path=str(file_path),
                    executable=executable,
                )

            # Styled Tree
            # Props: Dark mode, dense, accordion
            ui.tree(nodes=tree_items, on_select=open_code_file).classes(
                "w-full text-neutral-400 text-sm font-mono"
            ).props("dark dense no-connectors selected-color=emerald").expand()


async def create_new_file_dialog(scripts_path):
    # Tech Dialog
    with ui.dialog() as dialog, ui.card().classes("tech-dialog w-96 p-0 rounded overflow-hidden"):
        with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
            ui.label("NEW_SCRIPT").classes("text-sm font-bold tracking-widest text-emerald-500 font-mono")
            ui.button(icon="close", on_click=dialog.close).props("dense flat size=sm color=grey")

        with ui.column().classes("p-4 gap-4 w-full"):
            input_file_name = ui.input("FILENAME").props("outlined dense dark color=emerald").classes("w-full")

        with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"):
            ui.button("CANCEL", on_click=dialog.close).props("flat dense color=grey no-caps")
            ui.button("CREATE", on_click=lambda: on_create()).props(
                "unelevated dense color=emerald text-color=white no-caps"
            )

    async def on_create():
        success = await create_new_file(scripts_path, input_file_name.value)
        # if it waas created successfully, close the dialog automatically
        if success:
            dialog.close()

    dialog.open()


async def create_new_file(file_path: str, file_name: str) -> bool:
    # Same logic, just adding type safety for my sanity
    check_type(file_path, str, "file_path")
    check_type(file_name, str, "file_name")

    base_path = Path(file_path).resolve()
    full_path = base_path / file_name

    if not full_path.resolve().is_relative_to(base_path):
        ui.notify("Directory traversal detected", type="negative")
        ui.label("The image of shame will be displayed until you put in a valid file path/name")
        ui.image("/static/master_hacker.png")
        return False

    try:
        with open(full_path, "w") as f:
            f.write("")
        ui.notify(f"Created {file_name}", type="positive", color="emerald-9")
        file_picker.refresh()
        return True
    except Exception as e:
        ui.notify(f"Error: {e}", type="negative")
        return False


# -------------------------------
# IDE COMPONENT
# -------------------------------
async def ide_setup():
    global ide_tabs_parent, ide_panels_parent

    # Wrapper
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel rounded-none border-0"):
        # Header
        with ui.row().classes("w-full items-center bg-black/20 border-b border-white/5 px-2 h-10 gap-2"):
            ui.icon("code", size="xs", color="emerald-500")
            ui.label("EDITOR //").classes("tech-label-subtitle mr-4")

            # Tabs
            ide_tabs_parent = ui.tabs().props(
                "dense indicator-color=emerald text-color=grey-5 active-color=emerald-400 narrow-indicator align=left"
            )
            ide_tabs_parent.classes("bg-transparent h-full")

        # Body
        ide_panels_parent = (
            ui.tab_panels(ide_tabs_parent)
            .classes("w-full h-full bg-neutral-900/40")
            .props("dense transition-duration=0")
        )


async def code_editor(file_path: str, script_output_terminal_tab_name: str, executable=False):
    check_type(file_path, str, "file_path")

    async def load_file():
        with open(file_path, "r+") as file:
            return file.read()

    file_contents = await load_file()

    # Layout: Editor Left, Tools Right
    with ui.splitter(value=95, limits=(90, 98)).classes("w-full h-full").props(
        "separator-class=bg-white/5 separator-style=width:1px"
    ) as splitter:
        # Editor
        with splitter.before:
            editor = ui.codemirror(file_contents, theme="androidstudio", language="Python").classes(
                "h-full w-full outline-none text-sm font-mono"
            )

        # Toolbar
        with splitter.after:  # noqa: SIM117
            with ui.column().classes("h-full w-full bg-black/20 items-center py-2 gap-2 border-l border-white/5"):
                # Run
                if executable:
                    with (
                        ui.button(
                            on_click=lambda: open_tab_and_execute_script(
                                script_output_terminal_tab_name, script_path=file_path
                            )
                        )
                        .classes("tech-btn-action")
                        .props("flat round dense size=sm")
                    ):
                        ui.icon("play_arrow", size="xs")
                        ui.tooltip("Execute")

                ui.separator().classes("bg-white/10 w-4")

                # Save
                async def save_logic():
                    with open(file_path, "w") as f:
                        f.write(editor.value)
                    ui.notify("Saved", type="positive", color="emerald-9")

                with ui.button(on_click=save_logic).classes("tech-btn-ghost").props("flat round dense size=sm"):
                    ui.icon("save", size="xs")
                    ui.tooltip("Quick Save")

                # Save As (Dialog)
                async def open_save_as():
                    with ui.dialog() as d, ui.card().classes("tech-dialog w-96 p-0"):
                        with ui.row().classes("bg-neutral-900/50 p-4 border-b border-white/5"):
                            ui.label("SAVE_AS").classes("text-sm font-bold text-emerald-500 font-mono")

                        with ui.column().classes("p-4 gap-4"):
                            new_name = (
                                ui.input("FILENAME", value=Path(file_path).name)
                                .props("outlined dense dark color=emerald")
                                .classes("w-full")
                            )

                        with ui.row().classes("bg-black/20 p-4 border-t border-white/5 justify-end"):
                            ui.button("SAVE", on_click=lambda: finalize_save()).props("unelevated dense color=emerald")

                        def finalize_save():
                            new_p = Path(file_path).parent / new_name.value
                            with open(new_p, "w") as f:
                                f.write(editor.value)
                            d.close()
                            file_picker.refresh()
                            ui.notify("Saved new file")

                    d.open()

                with ui.button(on_click=open_save_as).classes("tech-btn-ghost").props("flat round dense size=sm"):
                    ui.icon("save_as", size="xs")
                    ui.tooltip("Save As...")

                # Reload
                async def reload_logic():
                    editor.value = await load_file()
                    ui.notify("Reloaded from disk")

                with ui.button(on_click=reload_logic).classes("tech-btn-ghost").props("flat round dense size=sm"):
                    ui.icon("refresh", size="xs")
                    ui.tooltip("Reload from Disk")


async def ide_add_tab(tab_name: str, script_path: str, executable=False):
    global ide_tabs_parent, ide_panels_parent, ide_open_tabs
    check_type(tab_name, str, "tab_name")

    if tab_name in ide_open_tabs:
        ide_panels_parent.set_value(tab_name)
        return

    # Create Tab
    with ide_tabs_parent, ui.tab(tab_name, label="").classes("h-full px-2 min-h-0") as tab:
        tab.meta = {"tab_name": tab_name}
        with ui.row().classes("items-center gap-2"):
            ui.icon("description", size="xs").classes("opacity-50")
            ui.label(tab_name).classes("text-xs font-mono")
            ui.button(icon="close", on_click=lambda tn=tab_name: ide_close_tab(tn)).props(
                "flat dense size=xs rounded"
            ).classes("text-neutral-500 hover:text-white")

    # Create Panel
    with ide_panels_parent, ui.tab_panel(tab_name).classes("p-0 w-full h-full") as panel:
        await code_editor(script_path, tab_name, executable=executable)

    ide_open_tabs[tab_name] = {"tab_object": tab, "panel_object": panel}
    ide_panels_parent.set_value(tab_name)


async def ide_close_tab(tab_name: str):
    global ide_tabs_parent, ide_panels_parent, ide_open_tabs
    try:
        tab_data = ide_open_tabs.pop(tab_name)
        ide_tabs_parent.remove(tab_data["tab_object"])
        ide_panels_parent.remove(tab_data["panel_object"])

        if ide_open_tabs:
            ide_panels_parent.set_value(next(iter(ide_open_tabs)))
        else:
            ide_panels_parent.set_value(None)
    except Exception as e:
        server_log.error(e)
