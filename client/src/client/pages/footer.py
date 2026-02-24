from nicegui import ui

from client.src.client.modules.latency_tracker import latency_status


async def build_footer():
    """Footer for API latency monitoring, and other data"""
    with ui.footer().classes("bg-[#0a0a0a] border-t border-white/5 py-1 px-4"):  # noqa: SIM117
        with ui.row().classes("w-full items-center justify-between"):
            with ui.row().classes("items-center gap-2"):
                ui.element("div").classes("w-1.5 h-1.5 rounded-full animate-pulse")

                ui.label().bind_text_from(
                    latency_status, "value", backward=lambda v: f"CLIENT -> SERVER LATENCY: {v}ms"
                ).classes("text-[10px] font-mono text-neutral-500")

            # could add in status of various core  components here too

            ui.label("LongHaulC2").classes("text-[10px] font-mono text-neutral-700")
