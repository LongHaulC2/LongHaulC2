import httpx
from nicegui import ui, events
import logging
from client.src.client.pages.menu import setup_menu
from client.src.client.utils.url import generate_url
from typing import Optional
import asyncio

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
                        await code_editor()
                    with horiz_splitter.after:
                        # ui.label("TERM BOTTOM").classes("w-full h-full")
                        await terminal()


async def code_editor():

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
        "def urmom():", theme="androidstudio", language="Python"
    ).classes("h-full w-full outline")
    # print(editor.supported_themes)


async def file_picker():
    ui.label("file_placeholder")


async def terminal():
    log = ui.log().classes("w-full h-full outline")
    log.push(
        "placeholder term - not final. hookup input and output of subprocess/thread that runs the scripts  to here"
    )
    # ui.label("term_placeholder")
