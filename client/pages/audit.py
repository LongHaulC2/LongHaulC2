import csv
import datetime
import io

import structlog
from nicegui import ui

from client.modules.api_calls import get_audit_export, get_audit_log
from client.pages.footer import build_footer
from client.pages.formatted_tooltip import formatted_tooltip
from client.pages.menu import setup_menu
from client.utils.helpers import notify

server_log = structlog.getLogger("server")

ACTION_LABELS = {
    "task_queued": ("TASK QUEUED", "emerald"),
    "implant_registered": ("IMPLANT REGISTERED", "blue"),
    "implant_deleted": ("IMPLANT DELETED", "red"),
    "listener_created": ("LISTENER CREATED", "blue"),
    "listener_started": ("LISTENER STARTED", "emerald"),
    "listener_stopped": ("LISTENER STOPPED", "amber"),
    "listener_deleted": ("LISTENER DELETED", "red"),
    "file_uploaded": ("FILE UPLOADED", "blue"),
    "file_deleted": ("FILE DELETED", "red"),
    "login_success": ("LOGIN", "emerald"),
    "login_failed": ("LOGIN FAILED", "red"),
    "user_registered": ("USER REGISTERED", "blue"),
    "user_deleted": ("USER DELETED", "red"),
}

PAGE_SIZES = [25, 50, 100]


@ui.page("/audit")
async def audit_page():
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Audit Log")
    await audit_view()
    await build_footer()


async def audit_view():
    state = {
        "entries": [],
        "total_count": 0,
        "page": 1,
        "page_size": 50,
    }

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        # Header
        with ui.row().classes("tech-header-bar flex w-full items-center justify-between shrink-0"):
            with ui.row().classes("items-center gap-4"):
                ui.icon("policy", size="sm", color="emerald-500").classes(
                    "p-2 bg-emerald-500/10 rounded border border-emerald-500/20"
                )
                with ui.column().classes("gap-0"):
                    ui.label("AUDIT LOG").classes("tech-label-header-bold")
                    ui.label("OPERATOR ACTIVITY TRACKING").classes("tech-label-sub text-emerald-500")

            with ui.row().classes("items-center gap-2"):
                with (
                    ui.button(on_click=lambda: download_page_csv())
                    .classes("tech-btn-action px-2")
                    .props("dense flat size=sm")
                ):
                    ui.icon("download", size="xs").classes("mr-1")
                    ui.label("CSV").classes("tech-label-sub")
                    formatted_tooltip("Download current page as CSV")

                with (
                    ui.button(on_click=lambda: download_all_csv())
                    .classes("tech-btn-action px-2")
                    .props("dense flat size=sm")
                ):
                    ui.icon("cloud_download", size="xs").classes("mr-1")
                    ui.label("ALL").classes("tech-label-sub")
                    formatted_tooltip("Download entire audit log as CSV")

                with (
                    ui.button(icon="refresh", on_click=lambda: load_data())
                    .props("dense flat size=sm")
                    .classes("tech-btn-secondary")
                ):
                    formatted_tooltip("Refresh")

        # Filters row
        with ui.row().classes("w-full h-10 gap-4 bg-[#0c0c0c] border-b border-white/5 items-center px-4 shrink-0"):
            filter_actor = (
                ui.input(placeholder="Actor")
                .props("dense dark borderless input-class=text-emerald-400 hide-bottom-space")
                .classes("w-32 text-xs")
            )
            filter_action = (
                ui.select(
                    options=[""] + list(ACTION_LABELS.keys()),
                    value="",
                    on_change=lambda: reset_and_load(),
                )
                .props("dense dark borderless options-dense label=Action")
                .classes("w-40 text-xs")
            )
            filter_target = (
                ui.select(
                    options=["", "implant", "listener", "file", "user"],
                    value="",
                    on_change=lambda: reset_and_load(),
                )
                .props("dense dark borderless options-dense label=Target")
                .classes("w-32 text-xs")
            )
            ui.button("FILTER", on_click=lambda: reset_and_load()).props("dense flat size=sm color=emerald").classes(
                "text-xs"
            )

        # Table area
        with ui.scroll_area().classes("w-full flex-grow"):
            table_container = ui.column().classes("w-full gap-0 p-0")

        # Pagination controls
        with ui.row().classes(
            "w-full h-10 items-center justify-between px-4 bg-[#0c0c0c] border-t border-white/5 shrink-0"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.label("Rows:").classes("font-mono text-[11px] text-neutral-500")
                ui.select(
                    options=PAGE_SIZES,
                    value=state["page_size"],
                    on_change=lambda e: on_page_size_change(e.value),
                ).props("dense dark borderless options-dense").classes("w-16 text-xs")

            page_info_label = ui.label("").classes("font-mono text-[11px] text-neutral-400")

            with ui.row().classes("items-center gap-1"):
                btn_first = (
                    ui.button(icon="first_page", on_click=lambda: go_to_page(1))
                    .props("dense flat size=sm color=grey")
                    .classes("text-xs")
                )
                btn_prev = (
                    ui.button(icon="chevron_left", on_click=lambda: go_to_page(state["page"] - 1))
                    .props("dense flat size=sm color=grey")
                    .classes("text-xs")
                )
                btn_next = (
                    ui.button(
                        icon="chevron_right",
                        on_click=lambda: go_to_page(state["page"] + 1),
                    )
                    .props("dense flat size=sm color=grey")
                    .classes("text-xs")
                )
                btn_last = (
                    ui.button(
                        icon="last_page",
                        on_click=lambda: go_to_page(total_pages()),
                    )
                    .props("dense flat size=sm color=grey")
                    .classes("text-xs")
                )

    def total_pages() -> int:
        if state["total_count"] == 0:
            return 1
        return max(1, -(-state["total_count"] // state["page_size"]))

    def get_filters():
        actor = (filter_actor.value.strip() or None) if filter_actor.value else None
        action = filter_action.value or None
        target_type = filter_target.value or None
        return actor, action, target_type

    def format_timestamp(ts_ms: int) -> str:
        return datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")

    def update_pagination_ui():
        tp = total_pages()
        start = ((state["page"] - 1) * state["page_size"]) + 1
        end = min(state["page"] * state["page_size"], state["total_count"])
        if state["total_count"] == 0:
            page_info_label.text = "0 entries"
        else:
            page_info_label.text = f"{start}-{end} of {state['total_count']}"

        btn_first.set_enabled(state["page"] > 1)
        btn_prev.set_enabled(state["page"] > 1)
        btn_next.set_enabled(state["page"] < tp)
        btn_last.set_enabled(state["page"] < tp)

    def render_table():
        table_container.clear()
        with table_container:
            with ui.row().classes(
                "w-full items-center px-4 py-2 border-b border-white/10 bg-black/40 gap-0 sticky top-0"
            ):
                ui.label("TIMESTAMP").classes("tech-label-sub w-[160px] shrink-0")
                ui.label("ACTOR").classes("tech-label-sub w-[100px] shrink-0")
                ui.label("ACTION").classes("tech-label-sub w-[180px] shrink-0")
                ui.label("TARGET").classes("tech-label-sub w-[80px] shrink-0")
                ui.label("TARGET UUID").classes("tech-label-sub w-[280px] shrink-0")
                ui.label("DETAIL").classes("tech-label-sub flex-grow")

            if not state["entries"]:
                with ui.column().classes("tech-empty-state w-full"):
                    ui.icon("policy", size="xl", color="emerald-5")
                    ui.label("No audit entries found").classes("tech-label-sub text-neutral-500")
                    ui.label("Activity will appear here as operators interact with the system").classes(
                        "tech-label-sub text-neutral-600 text-[10px]"
                    )
                return

            for entry in state["entries"]:
                action = entry.get("action", "")
                label, color = ACTION_LABELS.get(action, (action.upper(), "neutral"))

                with ui.row().classes(
                    "w-full items-center px-4 py-2 border-b border-white/5 hover:bg-white/5 transition-colors gap-0"
                ):
                    ui.label(format_timestamp(entry.get("timestamp", 0))).classes(
                        "font-mono text-[11px] text-neutral-400 w-[160px] shrink-0"
                    )
                    ui.label(entry.get("actor", "?")).classes(
                        "font-mono text-[11px] text-blue-400 w-[100px] shrink-0 truncate"
                    )
                    ui.label(label).classes(f"font-mono text-[11px] text-{color}-400 font-bold w-[180px] shrink-0")
                    ui.label(entry.get("target_type", "-") or "-").classes(
                        "font-mono text-[11px] text-neutral-500 w-[80px] shrink-0"
                    )
                    ui.label(entry.get("target_uuid", "-") or "-").classes(
                        "font-mono text-[11px] text-neutral-500 w-[280px] shrink-0"
                    )
                    ui.label(entry.get("detail", "-") or "-").classes(
                        "font-mono text-[11px] text-neutral-400 flex-grow truncate"
                    )

        update_pagination_ui()

    async def load_data():
        actor, action, target_type = get_filters()
        offset = (state["page"] - 1) * state["page_size"]

        result = await get_audit_log(
            actor=actor,
            action=action,
            target_type=target_type,
            limit=state["page_size"],
            offset=offset,
        )
        if result and result.get("status") == "200":
            data = result.get("data", {})
            state["entries"] = data.get("entries", [])
            state["total_count"] = data.get("total_count", 0)
        else:
            state["entries"] = []
            state["total_count"] = 0
            notify("Failed to load audit log", type="negative")
        render_table()

    async def reset_and_load():
        state["page"] = 1
        await load_data()

    async def go_to_page(page: int):
        tp = total_pages()
        page = max(1, min(page, tp))
        if page == state["page"]:
            return
        state["page"] = page
        await load_data()

    def on_page_size_change(new_size: int):
        state["page_size"] = new_size
        state["page"] = 1
        ui.timer(0, load_data, once=True)

    def download_page_csv():
        if not state["entries"]:
            notify("No data to export", type="warning")
            return

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "actor", "action", "target_type", "target_uuid", "detail"])

        for entry in state["entries"]:
            writer.writerow(
                [
                    format_timestamp(entry.get("timestamp", 0)),
                    entry.get("actor", ""),
                    entry.get("action", ""),
                    entry.get("target_type", ""),
                    entry.get("target_uuid", ""),
                    entry.get("detail", ""),
                ]
            )

        csv_bytes = output.getvalue().encode("utf-8")
        filename = f"audit_log_{datetime.datetime.now(tz=datetime.UTC).strftime('%Y%m%d_%H%M%S')}.csv"
        ui.download(csv_bytes, filename=filename, media_type="text/csv")

    async def download_all_csv():
        actor, action, target_type = get_filters()
        csv_bytes = await get_audit_export(actor=actor, action=action, target_type=target_type)
        if csv_bytes:
            filename = f"audit_log_full_{datetime.datetime.now(tz=datetime.UTC).strftime('%Y%m%d_%H%M%S')}.csv"
            ui.download(csv_bytes, filename=filename, media_type="text/csv")
        else:
            notify("Failed to export audit log", type="negative")

    await load_data()
