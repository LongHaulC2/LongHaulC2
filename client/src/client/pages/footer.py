import asyncio
from typing import Any

from nicegui import ui

from client.src.client.info import VERSION_NUMBER
from client.src.client.modules.api_calls import get_all_implant_data, get_all_listener_data
from client.src.client.modules.easter_eggs import run_random_easter_egg
from client.src.client.modules.latency_tracker import latency_status

# Using a dictionary with default values to prevent binding errors on first load
shitty_stats: dict[str, Any] = {"implant_count": "0", "listener_count": "0"}
# also, this poller makes it so that only one timer is going per user session
_poller_initialized = False


# ideas: A way to push to the footer, with a message, or a ui.notify wrapper that also puts a message in teh footer?


async def build_footer():
    """Footer for API latency monitoring, and other data"""
    global _poller_initialized

    # Only initialize the poller once per session to avoid hammering the API
    if not _poller_initialized:
        ui.timer(5, update_dashboard_stats)
        _poller_initialized = True

    with ui.footer().classes("bg-[#0a0a0a] border-t border-white/5 py-1 px-4"):  # noqa: SIM117
        with ui.row().classes("w-full items-center justify-between"):
            with ui.row().classes("items-center gap-4"):
                # Latency Group
                with ui.row().classes("items-center gap-2"):
                    ui.element("div").classes("w-1.5 h-1.5 rounded-full animate-pulse")

                    ui.label().bind_text_from(latency_status, "value", backward=lambda v: f"RTT: {v}ms").classes(
                        "text-[10px] font-mono text-neutral-500"
                    )

                ui.label("|").classes("tech-label-sub")

                # Stats Group
                with ui.row().classes("items-center gap-3"):
                    # Implant Count
                    with ui.row().classes("items-center gap-1"):
                        # ui.icon("sensors", size="12px").classes("text-neutral-600")
                        ui.label().bind_text_from(shitty_stats, "implant_count").classes(
                            "text-[10px] font-mono text-emerald-500/80"
                        )
                        ui.label("IMPLANTS").classes("tech-label-sub")

                    # Listener Count
                    with ui.row().classes("items-center gap-1"):
                        # ui.icon("settings_input_antenna", size="12px").classes("text-neutral-600")
                        ui.label().bind_text_from(shitty_stats, "listener_count").classes(
                            "text-[10px] font-mono text-amber-500/80"
                        )
                        ui.label("LISTENERS").classes("tech-label-sub")

                    # toss in easter egg out of the way

                    # setup semi random easter egg
                    run_random_easter_egg()

            ui.label(f"LONGHAULC2 // {VERSION_NUMBER}").classes(
                "text-[10px] font-mono text-neutral-700 tracking-tighter"
            )


async def update_dashboard_stats():
    """Function to update the local shitty_stats dictionary.  Meant to be called on a timer"""

    # get both at once, rather than seperate events
    results = await asyncio.gather(get_all_implant_data(), get_all_listener_data(), return_exceptions=True)

    implant_res = results[0] if not isinstance(results[0], Exception) else None
    shitty_stats["implant_count"] = str(len((implant_res or {}).get("data", [])))

    listener_res = results[1] if not isinstance(results[1], Exception) else None
    shitty_stats["listener_count"] = str(len((listener_res or {}).get("data", [])))
