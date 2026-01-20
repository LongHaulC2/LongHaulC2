import logging
from itertools import groupby
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
    get_payload_bytes,
    get_payload_data,
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


@ui.page("/payloads")
async def payloads():
    # HEY- readme: This is a hack to get the page full screen (and make h-full work). It should also allow for things like headers to fit without adjusting it manually
    # see the link below.
    # https://github.com/zauberzeug/nicegui/discussions/4049
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    ui.context.client.content.classes("h-full")

    setup_menu("payloads")

    await payloads_view()


async def payloads_view():
    """ """
    # Setup header
    with ui.row().classes("w-full items-center justify-between"):
        # LEFT: title / context
        ui.label("payloads").classes(f"text-h6 dense {TEXT_COLOR}")

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

    payload_data = (await get_payload_data()).get("data")
    await render_payloads(payload_data=payload_data)


async def render_payloads(payload_data: dict):
    """
    Renders expandable tables for payloads, grouped by Listener UUID.

    api_response: The full JSON dict from your API
                  (e.g. {'data': [...], 'status': '200', ...})
    """

    # 2. Define Table Columns
    columns = [
        {"name": "name", "label": "File Name", "field": "name", "align": "left"},
        {
            "name": "hash",
            "label": "Hash (MD5)",
            "field": "hash",
            "align": "left",
            "classes": "font-mono text-gray-500 text-xs",
        },
        {"name": "actions", "label": "Action", "field": "actions", "align": "right"},
    ]

    # 3. Group Data by Listener UUID
    #    Sort first (required for groupby)
    sorted_data = sorted(
        payload_data, key=lambda x: x.get("payload_listener_uuid", "Unknown")
    )

    grouped_payloads = {}
    for key, group in groupby(
        sorted_data, key=lambda x: x.get("payload_listener_uuid", "Unknown")
    ):
        grouped_payloads[key] = list(group)

    # 4. Action Handler
    async def handle_download(e):
        row = e.args
        ui.notify(f"Fetching {row['name']}...")

        # 1. Fetch bytes into NiceGUI memory
        file_bytes = await get_payload_bytes(row["hash"])

        if file_bytes:
            # 2. Trigger browser download from memory
            # Note: 'row['name']' ensures the file saves as 'myfile.exe', not 'download'
            # Note: can't use raw ui.download on endpoint, as ui.download can't auth to things
            ui.download(file_bytes, filename=row["name"])
            ui.notify("Download ready")
        else:
            ui.notify("Failed to fetch payload", type="negative")

    # 5. Render UI
    for listener_uuid, payloads in grouped_payloads.items():

        # Transform API data into Table Rows
        table_rows = []
        for p in payloads:
            table_rows.append(
                {
                    "id": p.get("id"),
                    "name": p.get(
                        "payload_name", "Unnamed"
                    ),  # Maps payload_name -> name
                    "hash": p.get("payload_hash", ""),  # Maps payload_hash -> hash
                    "uuid": listener_uuid,
                }
            )

        # Create Expansion Panel
        # can do another lookup for listener name/data iwth get_listener_data
        # or could just map it together with previous data.
        # inneficient. Just get all listeners at start
        listener_data = await get_listener_data(listener_uuid)
        listener_name = listener_data.get("data", {}).get("listener_name")
        label_text = f"Listener: {listener_name}: {listener_uuid}"

        with ui.expansion(label_text, icon="hub").classes("w-full"):

            table = (
                ui.table(columns=columns, rows=table_rows, row_key="id")
                .props("dense flat")
                .classes("w-full")
            )

            # Inject Download Button
            table.add_slot(
                "body-cell-actions",
                r"""
                <q-td :props="props">
                    <q-btn icon="download" flat dense round size="sm" color="primary" 
                        @click="$parent.$emit('download', props.row)" />
                </q-td>
                """,
            )

            table.on("download", handle_download)

        ui.separator()


async def start_payload_dialogue():
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
        name = implant_name_field.value
        listener_name = implant_listener_field.value
        variant = implant_variant_field.value
        output_format = implant_format_field.value

        # Validation
        if not all([name, listener_name, output_format]):
            ui.notify("Please fill in all required fields", type="warning")
            return

        if implant_variant_field.visible and not variant:
            ui.notify("Please select a communication variant", type="warning")
            return

        dialog_spinner.visible = True

        # Get the UUID based on the name selected
        listener_uuid = listener_uuid_map.get(listener_name)

        # Call build service
        result = await build_implant(
            implant_name=name,
            implant_listener_uuid=listener_uuid,
            implant_variant=variant if implant_variant_field.visible else None,
            output_format=output_format,
        )

        dialog_spinner.visible = False

        if not result:
            ui.notify("Implant build failed", type="negative")
            return

        ui.notify(f"Implant '{name}' build started ({output_format})", type="positive")
        dialog.close()

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
        with ui.card().classes(
            "w-[600px] max-w-full p-6 space-y-4 rounded-xl shadow-lg"
        ):

            # --- Header ---
            with ui.column().classes("w-full items-center gap-1"):
                ui.label("Build Implant").classes("text-xl font-bold tracking-tight")
                ui.label("Compile a new agent configuration").classes(
                    "text-sm text-gray-400"
                )

            ui.separator().classes("my-2")

            # --- Row 1: Identity & Output (Side-by-Side) ---
            with ui.row().classes("w-full gap-4"):
                # Name gets more space (flex-grow)
                implant_name_field = (
                    ui.input("Implant Name", placeholder="e.g., win_update_agent")
                    .props("outlined dense")
                    .classes("flex-grow")
                )

                # Format gets fixed width or smaller flex
                implant_format_field = (
                    ui.select(
                        options=["exe", "dll", "ps1", "shellcode", "all"],
                        value="exe",
                        label="Format",
                    )
                    .props("outlined dense")
                    .classes("w-32")  # Fixed width keeps it tidy
                )

            # --- Row 2: Connection Settings ---
            # Listener is the primary choice, so it gets a full row
            implant_listener_field = (
                ui.select(
                    options=list(listener_type_map.keys()),
                    label="Select Listener",
                    on_change=_on_listener_change,
                )
                .props("outlined dense options-dense")
                .classes("w-full")
            )

            # --- Row 3: Dynamic Variant (Full Width) ---
            # This appears conditionally but takes full width when shown
            implant_variant_field = (
                ui.select(
                    options=[],
                    label="Implementation Variant",
                )
                .props("outlined dense options-dense")
                .classes("w-full")
            )
            implant_variant_field.visible = False

            # --- Footer ---
            ui.separator().classes("mt-4 mb-2")

            # Spinner centered or near buttons
            dialog_spinner = ui.spinner(size="sm").classes("self-center")
            dialog_spinner.visible = False

            with ui.row().classes("w-full justify-between items-center"):
                # Place spinner on left (optional) or hidden
                ui.element("div")  # Spacer if spinner is hidden

                with ui.row().classes("gap-3"):
                    ui.button("Cancel", on_click=dialog.close).props("flat color=grey")
                    ui.button(
                        "Build Payload", icon="construction", on_click=_build_implant
                    ).props("unelevated color=primary")

    dialog.open()
