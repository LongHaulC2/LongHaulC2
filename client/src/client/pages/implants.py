import logging
from pathlib import Path

import httpx
from nicegui import ui
from nicegui.events import KeyEventArguments

from client.src.client.modules.api_calls import (
    get_all_implant_data,
    get_all_listener_data,
    get_implant_task_history,
    get_implant_task_history_since_uuid,
    get_listener_data,
    queue_task,
    start_listener,
    stop_listener,
    update_implant,
)
from client.src.client.modules.task_definitions import ResultType, task_tree
from client.src.client.pages.menu import setup_menu
from client.src.client.pages.notes import open_notes_dialog

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

server_log.info("Loading /listeners page")


@ui.page("/implants")
async def implants():
    # HEY- readme: This is a hack to get the page full screen (and make h-full work). It should also allow for things like headers to fit without adjusting it manually
    # see the link below.
    # https://github.com/zauberzeug/nicegui/discussions/4049
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    ui.context.client.content.classes("h-full")

    setup_menu("Implants")

    await implants_view()


async def implants_view():
    """ """
    # Setup header
    with ui.row().classes("w-full items-center justify-between"):
        # LEFT: title / context
        ui.label("Implants").classes(f"text-h6 dense {TEXT_COLOR}")

        with ui.row().classes("items-center q-gutter-xs"):

            # RIGHT: action buttons
            with ui.row().classes("items-center q-gutter-xs"):

                with ui.button(icon="add", on_click=lambda: ...).props(
                    "dense flat round"
                ).classes(f"[&_.q-icon]:{ICON_COLOR}"):
                    ui.tooltip("Add listener")

                with ui.button(icon="refresh", on_click=lambda: ...).props(
                    "dense flat round"
                ).classes(f"[&_.q-icon]:{ICON_COLOR}"):
                    ui.tooltip("Force Refresh listeners table")

    ui.separator()

    # example layout

    # with ui.expansion("Listener Name", icon="work").classes("w-full"):
    #     for i in range(1, 5):
    #         with ui.row().classes("w-full"):
    #             ui.label("inside the expansion - maybe table this")
    #             ui.label("<file_name>")
    #             ui.label("<file_hash>")
    #             ui.button("Download")
    #             ui.separator()
    rows = [
        {"name": "file_alpha.txt", "hash": "39a84b", "status": "Ready"},
        {"name": "file_beta.log", "hash": "10c92d", "status": "Ready"},
        {"name": "file_gamma.py", "hash": "55f12e", "status": "Archived"},
    ]

    columns = [
        {"name": "name", "label": "File Name", "field": "name", "align": "left"},
        {
            "name": "hash",
            "label": "Hash",
            "field": "hash",
            "align": "left",
            "classes": "font-mono text-gray-500",
        },
        {"name": "actions", "label": "Download", "field": "actions", "align": "right"},
    ]

    for i in range(1, 5):
        with ui.expansion("Listener Name", icon="table_view").classes("w-full"):
            # 'dense' makes rows shorter, 'flat' removes the table shadow
            table = (
                ui.table(columns=columns, rows=rows, row_key="name")
                .props("dense flat")
                .classes("w-full")
            )

            # Use a slot to inject a button into the table
            table.add_slot(
                "body-cell-actions",
                r"""
                <q-td :props="props">
                    <q-btn icon="download" flat dense round size="sm" color="primary" 
                        @click="$parent.$emit('download', props.row)" />
                </q-td>
            """,
            )

            # Python handler for the Vue event
            table.on("download", lambda e: ui.notify(f"Downloading {e.args['name']}"))
        ui.separator()
