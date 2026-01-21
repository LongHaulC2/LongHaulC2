import asyncio
import logging
from typing import Optional

import httpx
from nicegui import events, ui

from client.src.client.pages.menu import setup_menu
from client.src.client.style import TEXT_COLOR
from client.src.client.utils.url import generate_url

from ..utils.checks import check_type

server_log = logging.getLogger("server")
server_log.info("Loading /search page")


@ui.page("/search")
async def search():
    # 1. Full Screen Layout Setup
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Event Search")
    await search_view()


async def search_view():

    # Global state for the search logic
    api = httpx.AsyncClient()
    running_query: Optional[asyncio.Task] = None

    # --- UI LAYOUT ---

    # 1. Main Glass Panel
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):

        # 2. Header Bar
        with ui.row().classes("w-full items-center justify-between tech-header-bar"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("manage_search", color="emerald-500").classes("text-xl")
                ui.label("GLOBAL_SEARCH //").classes("tech-label-title")

        # 3. Command Bar (Search Inputs)
        with ui.row().classes(
            "w-full p-4 border-b border-white/5 bg-black/20 gap-4 items-center"
        ):

            # Search Type Dropdown
            # Using a styled select instead of a dropdown button for cleaner UI
            search_type = (
                ui.select(
                    options=["Implant Search", "Task Search"],
                    value="Implant Search",
                    label="MODE",
                )
                .props("outlined dense dark color=emerald options-dense")
                .classes("w-48")
            )

            # Search Input
            search_field = (
                ui.input(
                    placeholder="Enter query...",
                )
                .props(
                    "outlined dense dark color=emerald input-class=text-emerald-400 autofocus"
                )
                .classes("flex-grow")
            )

            with search_field.add_slot("prepend"):
                ui.icon("search", color="emerald-500")

            # Spinner (Hidden by default)
            search_spinner = ui.spinner(size="sm", color="emerald-500").classes(
                "opacity-0 transition-opacity"
            )

        # 4. Results Area
        with ui.column().classes(
            "w-full flex-grow relative overflow-hidden bg-transparent"
        ) as results_container:
            # Initial Empty State
            with ui.column().classes(
                "w-full h-full items-center justify-center opacity-30"
            ):
                ui.icon("radar", size="6em")
                ui.label("AWAITING INPUT").classes(
                    "font-mono text-sm mt-4 tracking-widest"
                )

    # --- LOGIC ---

    async def run_search(e: events.ValueChangeEventArguments) -> None:
        nonlocal running_query

        # UI Feedback
        search_spinner.classes(remove="opacity-0")  # Show spinner

        if running_query:
            running_query.cancel()

        # Determine Endpoint & Layout
        if search_type.value == "Implant Search":
            url = generate_url("/api/v1/implants/search")
            display_func = implants_list_layout
        elif search_type.value == "Task Search":
            url = generate_url("/api/v1/implants/history/search")
            display_func = tasks_list_layout

        # Clear previous results
        results_container.clear()

        # If empty input, reset to empty state
        if not search_field.value:
            search_spinner.classes(add="opacity-0")
            with results_container:
                with ui.column().classes(
                    "w-full h-full items-center justify-center opacity-30"
                ):
                    ui.icon("radar", size="6em")
                    ui.label("AWAITING INPUT").classes(
                        "font-mono text-sm mt-4 tracking-widest"
                    )
            return

        request_body = {"search_term": search_field.value}

        async def fetch():
            try:
                resp = await api.post(url, json=request_body)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])

                    # Render Results
                    with results_container:
                        if not data:
                            with ui.column().classes(
                                "w-full h-1/2 items-center justify-center opacity-50"
                            ):
                                ui.label("NO MATCHES FOUND").classes(
                                    "font-mono text-sm text-red-400"
                                )
                        else:
                            await display_func(data=data)
            except Exception as err:
                server_log.error(f"Search error: {err}")
            finally:
                search_spinner.classes(add="opacity-0")  # Hide spinner

        running_query = asyncio.create_task(fetch())
        try:
            await running_query
        except asyncio.CancelledError:
            pass

    # Attach Handler
    search_field.on_value_change(run_search)


# --- LAYOUT RENDERERS ---


async def implants_list_layout(data: list[dict]):
    """Renders the Implant Search Results Table"""
    check_type(data, list, "data")

    if not data:
        return

    # Tech Table Setup
    first_row = data[0]
    cols = [
        {
            "name": key,
            "label": key.replace("_", " ").title(),
            "field": key,
            "sortable": True,
            "align": "left",
        }
        for key in first_row.keys()
    ]

    table = (
        ui.table(columns=cols, rows=data, row_key="implant_uuid", pagination=50)
        .classes("w-full h-full no-shadow bg-transparent text-neutral-300")
        .props("dense flat virtual-scroll square")
    )

    # Custom Header styling (Dark/Tech)
    table.add_slot(
        "header",
        r"""
        <q-tr :props="props" class="bg-white/5 text-neutral-400 uppercase text-xs tracking-wider border-b border-white/10">
            <q-th v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.label }}
            </q-th>
        </q-tr>
    """,
    )

    # Notes Column Rendering
    table.add_slot(
        "body-cell-notes",
        r"""
        <q-td :props="props">
            <div style="max-height: 20px; max-width: 300px; overflow: hidden;" class="opacity-70 text-xs font-mono"> 
                <span v-if="props.row.notes" v-html="props.row.notes"></span>
            </div>
        </q-td>
    """,
    )


async def tasks_list_layout(data):
    """Renders the Task Search Results Table"""
    check_type(data, list, "data")

    if not data:
        return

    first_row = data[0]
    cols = [
        {
            "name": key,
            "label": key.replace("_", " ").title(),
            "field": key,
            "sortable": True,
            "align": "left",
        }
        for key in first_row.keys()
        if key not in ["task_request", "task_response"]  # Hide raw JSON
    ]

    table = (
        ui.table(columns=cols, rows=data, row_key="task_uuid", pagination=50)
        .classes("w-full h-full no-shadow bg-transparent text-neutral-300")
        .props("dense flat virtual-scroll square")
    )

    # Custom Header styling
    table.add_slot(
        "header",
        r"""
        <q-tr :props="props" class="bg-white/5 text-neutral-400 uppercase text-xs tracking-wider border-b border-white/10">
            <q-th v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.label }}
            </q-th>
        </q-tr>
    """,
    )

    # Notes Rendering
    table.add_slot(
        "body-cell-notes",
        r"""
        <q-td :props="props">
            <div style="max-height: 20px; max-width: 300px; overflow: hidden;" class="opacity-70 text-xs font-mono"> 
                <span v-if="props.row.notes" v-html="props.row.notes"></span>
            </div>
        </q-td>
    """,
    )
