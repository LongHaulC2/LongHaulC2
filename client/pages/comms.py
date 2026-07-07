import datetime

import structlog
from nicegui import app, ui

from client.modules.api_calls import get_chat_messages, send_chat_message
from client.pages.footer import build_footer
from client.pages.menu import setup_menu
from client.utils.helpers import notify

server_log = structlog.getLogger("server")


@ui.page("/comms")
async def comms_page():
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Chat")
    await chat_view()
    await build_footer()


async def chat_view():
    username = app.storage.user.get("username", "operator")
    state = {"last_id": 0, "messages": []}

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        # Header
        with ui.row().classes(  # noqa: SIM117
            "tech-header-bar flex w-full items-center justify-between shrink-0"
        ), ui.row().classes("items-center gap-4"):
            ui.icon("chat", size="sm", color="emerald-500").classes(
                "p-2 bg-emerald-500/10 rounded border border-emerald-500/20"
            )
            with ui.column().classes("gap-0"):
                ui.label("OPERATOR CHAT").classes("tech-label-header-bold")
                ui.label(f"LOGGED IN AS // {username.upper()}").classes("tech-label-sub text-emerald-500")

        # Messages area
        with ui.scroll_area().classes("w-full flex-grow p-4 bg-black/40") as scroll_area:
            message_container = ui.column().classes("w-full gap-1")

        # Input area
        with ui.row().classes("w-full p-4 gap-4 border-t border-white/5 shrink-0 bg-[#0c0c0c] items-center no-wrap"):
            ui.label(">").classes("tech-label-header-bold text-emerald-500 text-xl")

            chat_input = (
                ui.input(placeholder="Type a message...")
                .props("dense dark border color=emerald input-class=text-emerald-400 hide-bottom-space")
                .classes("flex-grow tech-input items-center")
            )

            ui.button("SEND", icon="send", on_click=lambda: handle_send()).classes(
                "tech-btn-action px-4 font-bold tracking-wide"
            ).props("unelevated dense")

    def render_messages():
        message_container.clear()
        with message_container:
            if not state["messages"]:
                with ui.column().classes("tech-empty-state w-full mt-8"):
                    ui.icon("chat_bubble_outline", size="xl", color="emerald-5")
                    ui.label("No messages yet").classes("tech-label-sub text-neutral-500")
                return

            for msg in state["messages"]:
                ts_ms = msg.get("timestamp", 0)
                ts_str = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.UTC).strftime("%H:%M:%S")
                sender = msg.get("sender", "?")
                text = msg.get("message", "")

                is_self = sender == username
                sender_color = "emerald" if is_self else "blue"

                with ui.column().classes("w-full gap-0 hover:bg-white/5 px-2 py-1 rounded transition-colors"):
                    with ui.row().classes("items-center gap-2"):
                        ui.label(sender).classes(f"font-mono text-xs font-bold text-{sender_color}-500")
                        ui.label(ts_str).classes("font-mono text-[10px] text-neutral-600")
                    ui.separator().classes("bg-white/5 my-0.5")
                    ui.markdown(text).classes("text-sm text-neutral-300 break-words [&>p]:m-0")

        ui.timer(0.05, lambda: scroll_area.scroll_to(percent=1.0), once=True)

    async def handle_send():
        text = chat_input.value.strip()
        if not text:
            return
        chat_input.value = ""
        result = await send_chat_message(text)
        if not result or result.get("status") != "200":
            notify("Failed to send message", type="negative")
            return
        await poll_messages()

    async def poll_messages():
        result = await get_chat_messages(since_id=state["last_id"])
        if not result or result.get("status") != "200":
            return
        new_messages = result.get("data", [])
        if not new_messages:
            return
        state["messages"].extend(new_messages)
        state["last_id"] = new_messages[-1].get("id", state["last_id"])
        render_messages()

    chat_input.on("keydown.enter", handle_send)

    await poll_messages()
    ui.timer(app.storage.user.get("auto_refresh_rate", 2), poll_messages)
