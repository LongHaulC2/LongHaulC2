from nicegui import app, ui

from client.pages.formatted_tooltip import formatted_tooltip


def flat_stat(label: str, value: str, icon: str, color: str = "emerald"):
    with ui.element("div").classes("tech-stat-pill flex-1 min-w-max"):
        ui.icon(icon, size="14px", color=f"{color}-500").classes("opacity-70")
        ui.label(label).classes("tech-label-sub")
        ui.label(str(value)).classes("tech-data-mono")


def stat_widget(label: str, icon: str, color: str, key: str, stats_dict: dict):
    with ui.element("div").classes("flex-1 h-full px-4 gap-2 flex items-center border-r border-white/5 bg-white/2"):
        ui.icon(icon, size="14px", color=f"{color}-500").classes("opacity-70")
        ui.label(label).classes("tech-label-sub")
        ui.label().bind_text_from(stats_dict, key).classes("tech-label-sub")


def info_row(key: str, value: str):
    with ui.row().classes(
        "w-full justify-between items-center py-2 border-b border-white/5 hover:bg-white/5 transition-colors"
    ):
        ui.label(key).classes("tech-label-sub")
        ui.label(str(value)).classes("tech-data-mono break-all text-right max-w-[60%]")


def empty_state(icon: str, message: str, action_label: str = "", on_action=None):
    with ui.column().classes("tech-empty-state w-full"):
        ui.icon(icon, size="xl", color="emerald-500")
        ui.label(message).classes("tech-label-sub text-neutral-500")
        if action_label and on_action:
            ui.button(action_label, icon="add", on_click=on_action).classes("tech-btn-action px-4").props(
                "dense flat size=sm"
            )


def confirm_action(title: str, message: str, on_confirm, confirm_label: str = "CONFIRM", icon: str = "warning"):
    with ui.dialog() as dialog, ui.card().classes("tech-confirm-dialog w-[420px] p-0 rounded overflow-hidden"):
        with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center gap-3"):
            ui.icon(icon, color="red-500")
            ui.label(title).classes("tech-label-sub text-red-400 font-bold")

        with ui.column().classes("p-5 gap-2 w-full"):
            ui.label(message).classes("text-sm font-mono text-neutral-300 leading-relaxed")

        with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"):
            ui.button("CANCEL", on_click=dialog.close).props("flat dense color=grey no-caps")

            async def do_confirm():
                dialog.close()
                await on_confirm()

            ui.button(confirm_label, on_click=do_confirm).props("unelevated dense color=red no-caps").classes(
                "font-bold tracking-wide"
            )

    dialog.open()


async def back_button():
    await ui.context.client.connected()
    prev_uri = app.storage.tab.get("previous_uri", "/")
    with (
        ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to(prev_uri))
        .props("flat dense square size=sm")
        .classes("tech-btn-ghost")
    ):
        formatted_tooltip(prev_uri)
