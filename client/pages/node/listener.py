import structlog
from nicegui import ui

from client.modules.api_calls import (
    delete_listener,
    get_listener_data,
    preview_profile,
    restart_listener,
    start_listener_from_existing,
    stop_listener,
)
from client.pages.components.dashboard_widgets import back_button, flat_stat
from client.pages.components.metadata_view import MetadataView
from client.pages.components.notes_editor import GenericNotesEditor
from client.pages.footer import build_footer
from client.pages.formatted_tooltip import formatted_tooltip
from client.pages.menu import setup_menu

server_log = structlog.getLogger("server")


# ========================================
#   PAGE LOGIC
# ========================================


@ui.page("/listener/{listener_uuid}")
async def listener_details(listener_uuid: str):
    # Layout Setup
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Listener View")

    # Fetch listener listener_data
    api_res = await get_listener_data(listener_uuid)
    listener_data = api_res.get("data", {}) or {}

    # Render Dashboard
    await render_dashboard(listener_data, listener_uuid)
    await build_footer()


# ========================================
# dashboard
# ========================================
async def render_dashboard(listener_data: dict, listener_uuid: str):
    profile_toml = listener_data.get("listener_profile_contents", "")

    # MAIN CONTAINER
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        # ====================
        #   1. HEADER
        # ====================
        with ui.row().classes("tech-header-bar flex w-full items-center justify-between shrink-0"):
            with ui.row().classes("items-center gap-4"):
                await back_button()
                ui.icon("headphones", size="sm", color="emerald-500").classes(
                    "p-2 bg-emerald-500/10 rounded border border-emerald-500/20"
                )
                with ui.column().classes("gap-0"):
                    ui.label(f"{listener_uuid}").classes("tech-label-header-bold")
                    ui.label(f"LISTENER // {listener_data.get('listener_host', '0.0.0.0')}").classes(
                        "tech-label-sub text-emerald-500"
                    )

            with ui.row().classes("items-center gap-2"):
                with ui.button(
                    "START",
                    icon="play_arrow",
                    on_click=lambda: start_listener_from_existing(listener_uuid=listener_uuid),
                ).props("flat dense color=green no-caps size=sm"):
                    formatted_tooltip(
                        title="Start a stopped listener",
                        body=("The listener must already exist to be restarted."),
                        footer="To spawn a new listener, click the '+ listener' button",
                    )

                with ui.button(
                    "RESTART", icon="restart_alt", on_click=lambda: restart_listener(listener_uuid=listener_uuid)
                ).props("flat dense color=orange no-caps size=sm"):
                    formatted_tooltip(
                        title="Restart the Listener",
                        body=(
                            "Kill the current listener process, and re-spawn a new one with the same config. "
                            "This is handy for if a listener crashes, or encounters a bug."
                        ),
                    )

                with ui.button("STOP", icon="stop", on_click=lambda: stop_listener(listener_uuid=listener_uuid)).props(  # noqa
                    "flat dense color=red no-caps size=sm"
                ):
                    formatted_tooltip(
                        title="Stop Listener",
                        body=(
                            "Stops the listener process without deleting it.\n"
                            "The listener remains in the database,\n"
                            "is still a valid compile target,\n"
                            "and can be restarted at any time."
                        ),
                        footer="(Acts like a pause button)",
                    )

                with ui.button(
                    "DELETE", icon="delete", on_click=lambda: delete_listener(listener_uuid=listener_uuid)
                ).props("flat dense color=purple no-caps size=sm"):
                    # ui.tooltip("Stop, and DELETE a listener from the database. This listener will cease to exist.")
                    formatted_tooltip(
                        title="Delete Listener",
                        body=(
                            "Stops, and deletes the listener from the Database.\n"
                            "The listener will be nuked from existence via this action"
                        ),
                        footer="\n",  # add a \n so there's space at the bottom, and the whole message shows.
                    )

        # ====================
        #   2. VITALS BAR (Flat layout replacing stat_cards)
        # ====================
        with ui.row().classes(
            "w-full h-10 gap-0 bg-black/20 border-b border-white/5 items-center shrink-0 flex-nowrap overflow-x-auto"
        ):
            flat_stat("PROTOCOL", listener_data.get("listener_type", "?"), "headphones", "blue")
            flat_stat("NETWORK ADDR", listener_data.get("listener_host", "0.0.0.0"), "lan", "blue")
            flat_stat("NETWORK PORT", listener_data.get("listener_port", "0"), "lan", "blue")
            flat_stat("NETWORK PROFILE", listener_data.get("listener_profile_name", "0.0.0.0"), "code", "green")
            # flat_stat("CONNECTED IMPLANTS", listener_data.get("?", "?"), "lan", "blue")

        # ====================
        #   3. BODY
        # ====================
        with ui.row().classes("w-full flex-grow p-4 gap-4 overflow-hidden no-wrap items-stretch"):  # noqa - nicegui nested
            # --------------------
            # LEFT: WORKSPACE / TABS (Removed ui.card)
            # --------------------
            with ui.column().classes(
                "flex-grow min-w-0 bg-black/20 border border-white/5 rounded overflow-hidden flex-nowrap gap-0"
            ):
                # Tabs Header
                with ui.row().classes("w-full border-b border-white/5 bg-black/40 px-2 shrink-0"):
                    tabs = (
                        ui.tabs()
                        .classes("w-full text-left")
                        .props(
                            "dense indicator-color=emerald text-color=grey-5 active-color=emerald-400 align=left narrow-indicator"  # noqa
                        )
                    )
                    with tabs:
                        ui.tab("metadata_tab", label="METADATA").classes("h-10 min-h-0 tech-label-sub")

                        ui.tab("network_profile_tab", label="NET PROFILE [CONFIG]").classes(
                            "h-10 min-h-0 tech-label-sub"
                        )
                        ui.tab("network_profile_wire_tab", label="NET PROFILE [ON WIRE]").classes(
                            "h-10 min-h-0 tech-label-sub"
                        )

                        ui.tab("notes_tab", label="NOTES").classes("h-10 min-h-0 tech-label-sub")

                        # ui.tab("graph_tab", label="GRAPH").classes("h-10 min-h-0 tech-label-sub")

                # Tabs Content
                with ui.tab_panels(tabs, value="metadata_tab").classes("w-full flex-grow bg-transparent p-0"):
                    # Metadata Tab
                    with ui.tab_panel("metadata_tab").classes("w-full h-full p-0"):  # noqa
                        MetadataView(listener_data)

                    # Connected Implants Tab
                    with ui.tab_panel("connected_implants_tab").classes(
                        "w-full h-full items-center justify-center text-neutral-600"
                    ):  # noqa
                        ui.icon("hub", size="xl").classes("mb-2 opacity-50")
                        ui.label("connected implants NOT IMPLEMENTED").classes("tech-label-sub")

                    # network_profile_tab
                    with ui.tab_panel("network_profile_tab").classes("w-full h-full p-0"):
                        # using a UI log, it has builtins like scrolling, etc to make this easier.
                        # not a permanent solution, but works for now.
                        code_panel = ui.codemirror(profile_toml, theme="androidstudio", language="TOML").classes(
                            "w-full h-full"
                        )  # noqa
                        # sets panel to readonly
                        code_panel.set_enabled(False)

                    with ui.tab_panel("network_profile_wire_tab").classes("w-full h-full p-0"):
                        wire_container = ui.column().classes("w-full h-full overflow-auto")
                        if profile_toml.strip():
                            result = await preview_profile(profile_toml)
                            if result and result.get("data"):
                                with wire_container:
                                    from client.pages.profile_preview import _render_output

                                    _render_output(result["data"])
                            else:
                                with wire_container:
                                    ui.label("Failed to render profile preview").classes(
                                        "tech-label-sub text-red-400 p-4"
                                    )
                        else:
                            with wire_container:
                                ui.label("No profile data available").classes("tech-label-sub text-neutral-500 p-4")

                    with ui.tab_panel("notes_tab").classes("w-full h-full p-0"):  # noqa - nicegui
                        # hook me into genetic update func that takes node type, and contents?
                        with ui.column().classes("w-full h-full relative"):
                            GenericNotesEditor(
                                node_type="listener",
                                node_id=listener_uuid,
                            )
                    # Graph Tab
                    # with ui.tab_panel("graph_tab").classes(
                    #     "w-full h-full items-center justify-center text-neutral-600"
                    # ):
                    #     ui.icon("hub", size="xl").classes("mb-2 opacity-50")
                    #     ui.label("GRAPH MODULE NOT IMPLEMENTED").classes("tech-label-sub")

                # Footer Actions
                with ui.column().classes("w-full p-4 gap-2 border-t border-white/5 shrink-0 bg-black/20"):
                    ui.label("ACTIONS").classes("tech-label-sub")
                    # with ui.row().classes("w-full gap-2"):
                    # ui.button("KILL", icon="bolt").classes(
                    #     "flex-1 bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20 transition-colors"  # noqa
                    # ).props("unelevated dense")
                    # ui.button("EXIT", icon="logout").classes(
                    #     "!tech-btn-action w-full"  # noqa
                    # ).props("unelevated dense")
