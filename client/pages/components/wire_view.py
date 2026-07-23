import hexdump as hexdump_lib
from nicegui import ui


def _build_wire_text(body: str, token: str | None, transforms: list[dict]) -> str:
    """Construct the wire representation by replacing the token in the body template
    with the final transform result."""
    if not body:
        return "(empty)"
    wire = body
    if token and transforms:
        last_result = transforms[-1].get("result_display", "")
        wire = wire.replace(token, last_result)
    elif token and not transforms and token in wire:
        wire = wire.replace(token, "[raw payload bytes]")
    return wire


def _wire_block(
    label: str,
    direction: str,
    icon: str,
    body: str,
    token: str | None,
    transforms: list[dict],
    color: str,
    pre_classes: dict,
):
    """Render a single wire direction block."""
    wire_text = _build_wire_text(body, token, transforms)

    border_color = "emerald" if color == "emerald" else "amber"
    with ui.column().classes("w-full gap-0"):
        with ui.row().classes(
            f"items-center gap-2 px-3 py-2 border-l-2 border-{border_color}-500/40 bg-{border_color}-500/5"
        ):
            ui.icon(icon, size="xs", color=f"{border_color}-400").classes("opacity-70")
            ui.label(label).classes("tech-label-sub font-bold")
            ui.label(direction).classes("tech-label-sub text-neutral-600")

        if not body:
            ui.label("(not configured)").classes("tech-label-sub text-neutral-600 italic px-3 py-2")
            return

        wire_html = ui.html("").classes("w-full")

        def update_content():
            if pre_classes.get("hexdump", False):
                raw_bytes = wire_text.encode("latin-1", errors="replace")
                hex_str = hexdump_lib.hexdump(raw_bytes, result="return")
                hex_escaped = hex_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html_str = (
                    f'<pre style="margin:0;padding:12px;font-family:monospace;font-size:11px;'
                    f"color:#d4d4d4;background:#0d1117;border:1px solid rgba(255,255,255,0.05);"
                    f'border-radius:4px;white-space:pre;overflow-x:auto;">{hex_escaped}</pre>'
                )
                wire_html.set_content(html_str)
                return

            wrap = pre_classes.get("wrap", False)
            escapes = pre_classes.get("escapes", True)
            ws_style = "white-space:pre-wrap;word-break:break-all;" if wrap else "white-space:pre;overflow-x:auto;"
            content = wire_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if escapes:
                esc = '<span style="color:#ef5350;opacity:0.8;">'
                sentinel = "\x00NL\x00"
                content = content.replace("\\r\\n", f"{esc}\\r\\n</span>{sentinel}")
                content = content.replace("\r\n", f"{esc}\\r\\n</span>{sentinel}")
                content = content.replace("\r", f"{esc}\\r</span>{sentinel}")
                content = content.replace("\n", f"{esc}\\n</span>{sentinel}")
                content = content.replace(sentinel, "\n")
            else:
                content = content.replace("\\r\\n", "\n")
                content = content.replace("\r\n", "\n")
                content = content.replace("\r", "\n")
            html_str = (
                f'<pre style="margin:0;padding:12px;font-family:monospace;font-size:11px;'
                f"color:#d4d4d4;background:#0d1117;border:1px solid rgba(255,255,255,0.05);"
                f'border-radius:4px;{ws_style}">{content}</pre>'
            )
            wire_html.set_content(html_str)

        pre_classes["_updaters"] = pre_classes.get("_updaters", [])
        pre_classes["_updaters"].append(update_content)
        update_content()


def render_wire_view(data: dict):
    """Render Wireshark-style wire visualization from preview_profile() API response.
    Shows four vertically stacked blocks: GET req/resp, POST req/resp.
    Includes toggle controls for wrap and escape visibility."""

    # wrap on by default, so it wraps when items are too long, otherwise it goes off the edge and the show/wrap buttons
    # are hidden in a horizontal scroll
    toggle_state = {"wrap": True, "escapes": True, "hexdump": False, "_updaters": []}

    with ui.row().classes("items-center gap-4 px-4 py-2 border-b border-white/5 bg-black/20 w-full shrink-0"):
        ui.icon("cable", size="xs", color="emerald-400").classes("opacity-60")
        ui.label("WIRE VIEW").classes("tech-label-sub font-bold")
        ui.space()

        def on_wrap(e):
            toggle_state["wrap"] = e.value
            for fn in toggle_state.get("_updaters", []):
                fn()

        def on_escapes(e):
            toggle_state["escapes"] = e.value
            for fn in toggle_state.get("_updaters", []):
                fn()

        def on_hexdump(e):
            toggle_state["hexdump"] = e.value
            for fn in toggle_state.get("_updaters", []):
                fn()

        ui.switch("Wrap", value=True, on_change=on_wrap).props("dense size=sm color=emerald")
        ui.switch("Show \\r\\n", value=True, on_change=on_escapes).props("dense size=sm color=emerald")
        ui.switch("Hexdump", value=False, on_change=on_hexdump).props("dense size=sm color=emerald")

    entries = data.get("raw_profiles", [])
    if not entries:
        with ui.column().classes("w-full items-center justify-center py-8 opacity-40"):
            ui.icon("info", size="lg", color="neutral-500")
            ui.label("No raw profiles to visualize").classes("tech-label-sub text-neutral-500")
        return

    with ui.scroll_area().classes("w-full flex-grow"):
        for entry in entries:
            get_data = entry.get("get") or {}
            post_data = entry.get("post") or {}

            with ui.column().classes("w-full gap-4 p-4 pb-16"):
                _wire_block(
                    label="GET Request",
                    direction="client → server",
                    icon="call_made",
                    body=get_data.get("client", {}).get("body", ""),
                    token="<METADATA>",
                    transforms=get_data.get("client", {}).get("metadata_transforms", []),
                    color="emerald",
                    pre_classes=toggle_state,
                )

                _wire_block(
                    label="GET Response",
                    direction="server → client",
                    icon="call_received",
                    body=get_data.get("server", {}).get("body", ""),
                    token="<OUTPUT>",
                    transforms=get_data.get("server", {}).get("output_transforms", []),
                    color="amber",
                    pre_classes=toggle_state,
                )

                ui.separator().classes("bg-white/5")

                _wire_block(
                    label="POST Request",
                    direction="client → server",
                    icon="call_made",
                    body=post_data.get("client", {}).get("body", ""),
                    token="<OUTPUT>",
                    transforms=post_data.get("client", {}).get("output_transforms", []),
                    color="emerald",
                    pre_classes=toggle_state,
                )

                _wire_block(
                    label="POST Response (ACK)",
                    direction="server → client",
                    icon="call_received",
                    body=post_data.get("server", {}).get("body", ""),
                    token=None,
                    transforms=[],
                    color="amber",
                    pre_classes=toggle_state,
                )


def render_profile_output(data: dict):
    """Render profile wire visualization with an optional name/author header.
    This is the main entry point used by both the profile editor and the listener detail page."""

    profile_name = data.get("profile_name", "")
    profile_author = data.get("profile_author", "")
    if profile_name or profile_author:
        with ui.row().classes("items-center gap-3 px-4 py-2 border-b border-white/5 bg-black/20 w-full shrink-0"):
            ui.label(profile_name or "Unnamed Profile").classes("tech-label-sub text-emerald-400 font-bold")
            if profile_author:
                ui.label(f"by {profile_author}").classes("tech-label-sub text-neutral-500")

    render_wire_view(data)
