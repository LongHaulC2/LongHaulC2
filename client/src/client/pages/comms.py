import datetime

import structlog
from nicegui import ui

# Assuming these exist based on your architecture
from client.src.client.pages.footer import build_footer
from client.src.client.pages.menu import setup_menu

server_log = structlog.getLogger("server")


@ui.page("/comms")
async def comms_page():
    # Force full height to prevent weird scrolling overlaps
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("[POC - COMMS]")
    await chat_view()
    await build_footer()


async def chat_view():
    # Mock state
    state = {
        "messages": [
            {
                "sender": "SYSTEM",
                "text": "Encrypted channel established. Logging active.",
                "time": "00:00",
                "color": "orange",
            },
            {"sender": "IMPLANT_01", "text": "Checking in. Awaiting tasking.", "time": "00:01", "color": "blue"},
            {"sender": "IMPLANT_02", "text": "Heartbeat OK. Uploading loot.", "time": "00:03", "color": "purple"},
        ]
    }

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        # --- HEADER ---
        with ui.row().classes("tech-header-bar flex w-full items-center justify-between shrink-0"):
            with ui.row().classes("items-center gap-4"):
                ui.icon("terminal", size="sm", color="emerald-500").classes(
                    "p-2 bg-emerald-500/10 rounded border border-emerald-500/20"
                )
                with ui.column().classes("gap-0"):
                    ui.label("SECURE COMMS").classes("tech-label-header-bold")
                    ui.label("CHANNEL // GLOBAL_OP").classes("tech-label-sub text-emerald-500")

            with ui.row().classes("items-center gap-2"):
                ui.button(icon="delete_sweep", on_click=lambda: clear_chat()).props(
                    "flat dense square size=sm"
                ).classes("text-red-400 hover:text-red-200 transition-colors tech-btn-action-2")

                with ui.element("div").classes(
                    "flex items-center gap-2 px-3 py-1 bg-black/40 border border-white/5 rounded"
                ):
                    ui.icon("circle", size="8px", color="emerald-500").classes("animate-pulse")
                    ui.label("3 ONLINE").classes("tech-label-sub")

        # --- MESSAGES AREA ---
        # bg-black/40 creates that terminal depth feeling
        with ui.scroll_area().classes("w-full flex-grow p-4 bg-black/40") as scroll_area:
            message_container = ui.column().classes("w-full gap-1")

        # --- INPUT AREA ---
        with ui.row().classes("w-full p-4 gap-4 border-t border-white/5 shrink-0 bg-[#0c0c0c] items-center no-wrap"):
            ui.label(">").classes("tech-label-header-bold text-emerald-500 text-xl")

            chat_input = (
                ui.input(placeholder="Enter command or message...")
                .props("dense dark border color=emerald input-class=text-emerald-400 hide-bottom-space")
                .classes("flex-grow tech-input items-center")
            )

            send_btn = (  # noqa
                ui.button("TRANSMIT", icon="send", on_click=lambda: send_message())
                .classes("tech-btn-action px-4 font-bold tracking-wide")
                .props("unelevated dense")
            )

    # --- LOGIC ---
    def render_messages():
        """Re-renders the message list and forces the scroll area to the bottom."""
        message_container.clear()
        with message_container:
            for msg in state["messages"]:
                with ui.row().classes(
                    "w-full items-baseline gap-2 hover:bg-white/5 p-1 rounded transition-colors no-wrap"
                ):
                    # Timestamp
                    ui.label(f"[{msg['time']}]").classes("tech-label-sub text-neutral-500 min-w-max")
                    # Sender
                    ui.label(f"<{msg['sender']}>").classes(
                        f"tech-label-sub text-{msg['color']}-500 font-bold min-w-max"
                    )
                    # Content
                    ui.label(msg["text"]).classes("tech-data-mono text-neutral-300 break-words flex-grow")

        # UI hack to auto-scroll to bottom after render
        ui.timer(0.05, lambda: scroll_area.scroll_to(percent=1.0), once=True)

    def send_message():
        text = chat_input.value.strip()
        if not text:
            return

        now = datetime.datetime.now().strftime("%H:%M:%S")
        state["messages"].append({"sender": "LOCAL_ADMIN", "text": text, "time": now, "color": "emerald"})

        chat_input.value = ""
        render_messages()

    def clear_chat():
        state["messages"] = [
            {
                "sender": "SYSTEM",
                "text": "Buffer cleared.",
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "color": "orange",
            }
        ]
        render_messages()

    # Bind the Enter key to the send function
    chat_input.on("keydown.enter", send_message)

    # Initial paint
    render_messages()
