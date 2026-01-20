import logging
from pathlib import Path

import httpx
from nicegui import ui
from nicegui.events import KeyEventArguments

from client.src.client.modules.api_calls import (
    build_implant,
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

                with ui.button(
                    icon="add", on_click=lambda: start_implant_dialogue()
                ).props("dense flat round").classes(f"[&_.q-icon]:{ICON_COLOR}"):
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


async def start_implant_dialogue():
    """
    Opens a dialog to build a new implant.
    Fetches available listeners and dynamically updates available variants based on listener type.
    """

    # Map Listener Types -> List of available Implant Variants
    VARIANT_MAP = {
        "http": ["http_wininet"],
        # "ntp": ["ntp_default"],  # not imlpemetned
    }

    response = await get_all_listener_data()
    listeners_list = response.get("data", [])

    # Create Lookups
    # Map Name -> Type (used to determine which variants to show)
    listener_type_map = {l["listener_name"]: l["listener_type"] for l in listeners_list}

    # Map Name -> UUID (used to send the build command)
    listener_uuid_map = {l["listener_name"]: l["listener_uuid"] for l in listeners_list}

    # 4. Action Handler: Build
    async def _build_implant():
        implant_name = implant_name_field.value
        listener_name = implant_listener_field.value
        variant = implant_variant_field.value

        # Validation
        if not all([implant_name, listener_name]):
            ui.notify("Please fill in all required fields", type="warning")
            return

        # If the variant field is visible, we must ensure one is selected
        if implant_variant_field.visible and not variant:
            ui.notify("Please select a communication variant", type="warning")
            return

        dialog_spinner.visible = True

        # Get the UUID based on the name selected
        listener_uuid = listener_uuid_map.get(listener_name)

        # Call build service
        result = await build_implant(
            implant_name=implant_name,
            implant_listener_uuid=listener_uuid,
            implant_variant=variant if implant_variant_field.visible else None,
        )

        dialog_spinner.visible = False

        if not result:
            ui.notify("Implant build failed", type="negative")
            return

        ui.notify(f"Implant '{name}' build started", type="positive")
        dialog.close()
        # await refresh()

    # 5. UI Logic: Update Dropdown
    def _on_listener_change(e):
        """
        Triggered when listener dropdown changes.
        Updates the Variant dropdown options based on the listener type.
        """
        selected_name = e.value
        selected_type = listener_type_map.get(selected_name)

        # Look up valid variants for this listener type
        allowed_variants = VARIANT_MAP.get(selected_type, [])

        # if there's a variant available....
        if allowed_variants:
            # Update options dynamically
            implant_variant_field.options = allowed_variants
            implant_variant_field.value = allowed_variants[
                0
            ]  # Auto-select first option
            implant_variant_field.visible = True
            implant_variant_field.label = (
                f"{selected_type.upper()} Variant"  # Update label text
            )
        else:
            # Hide if no variants exist for this type
            implant_variant_field.options = []
            implant_variant_field.value = None
            implant_variant_field.visible = False

    # 6. Build the UI
    with ui.dialog() as dialog:
        with ui.card().classes("w-[600px] max-w-full p-6 space-y-4 rounded-xl"):

            # Header
            ui.label("Build Implant").classes("text-xl font-semibold text-center")
            ui.label("Compile a new agent for a specific listener").classes(
                "text-sm text-gray-500 text-center"
            )
            ui.separator()

            # Row 1: Implant Name
            with ui.row().classes("w-full gap-4"):
                implant_name_field = (
                    ui.input("Implant Name").props("outlined dense").classes("flex-1")
                )

            # Row 2: Listener Selection
            with ui.row().classes("w-full gap-4"):
                implant_listener_field = (
                    ui.select(
                        options=list(
                            listener_type_map.keys()
                        ),  # List of listener names
                        label="Select Listener",
                        on_change=_on_listener_change,  # Hook up logic
                    )
                    .props("outlined dense")
                    .classes("flex-1")
                )

            # Row 3: Variants (Dynamic)
            with ui.row().classes("w-full gap-4"):
                implant_variant_field = (
                    ui.select(
                        options=[],  # Empty start, populated by _on_listener_change
                        label="Implementation Variant",
                    )
                    .props("outlined dense")
                    .classes("flex-1")
                )
                implant_variant_field.visible = False  # Hidden by default

            ui.separator()

            # Spinner (Hidden)
            dialog_spinner = ui.spinner(size="sm")
            dialog_spinner.visible = False

            # Buttons
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", icon="close", on_click=dialog.close).props("flat")
                ui.button("Build", icon="construction", on_click=_build_implant).props(
                    "unelevated color=primary"
                )

    dialog.open()
