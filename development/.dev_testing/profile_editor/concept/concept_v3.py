import re
import tomllib
from pathlib import Path

from nicegui import ui, events


# ════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ════════════════════════════════════════════════════════════════════════════

TRANSFORMS = {
    "base64":    {"desc": "Standard Base64 encode/decode",       "input": False, "field": None,
                  "wire_in": "raw bytes", "wire_out": "ASCII text (A-Za-z0-9+/=)"},
    "base64url": {"desc": "URL-safe Base64 (no padding)",        "input": False, "field": None,
                  "wire_in": "raw bytes", "wire_out": "ASCII text (A-Za-z0-9-_)"},
    "prepend":   {"desc": "Prepend literal bytes before data",   "input": True,  "field": "val",
                  "wire_in": "any", "wire_out": "val bytes + original",
                  "val_hint": "Supports \\xNN hex escapes for raw bytes. Plain ASCII goes as-is.",
                  "val_example": "Text: 'GET /'  |  Binary: '\\x23\\x00\\x06\\xEC'  |  Mixed: 'GET /sid=\\x0D\\x0A'"},
    "append":    {"desc": "Append literal bytes after data",     "input": True,  "field": "val",
                  "wire_in": "any", "wire_out": "original + val bytes",
                  "val_hint": "Supports \\xNN hex escapes for raw bytes. Plain ASCII goes as-is.",
                  "val_example": "Text: ' HTTP/1.1'  |  Binary: '\\x0D\\x0A\\x0D\\x0A'"},
    "mask":      {"desc": "XOR with repeating key",              "input": True,  "field": "val",
                  "wire_in": "raw bytes", "wire_out": "raw bytes (same length)",
                  "val_hint": "XOR key as \\xNN hex bytes. Key repeats over the data.",
                  "val_example": "'\\xFF' (single byte)  |  '\\xDE\\xAD' (two-byte repeating)"},
    "netbios":   {"desc": "NetBIOS encoding (lowercase a-p)",    "input": False, "field": None,
                  "wire_in": "raw bytes", "wire_out": "ASCII text (2x size expansion)"},
    "netbiosu":  {"desc": "NetBIOS encoding (uppercase A-P)",    "input": False, "field": None,
                  "wire_in": "raw bytes", "wire_out": "ASCII text (2x size expansion)"},
    "symcrypt":  {"desc": "AES-256-GCM symmetric encryption",    "input": True,  "field": "key",
                  "wire_in": "raw bytes", "wire_out": "raw bytes (+28B: 12B nonce + 16B tag + ciphertext)",
                  "val_hint": "Exactly 32 bytes as \\xNN hex escapes. Must match the key compiled into the implant.",
                  "val_example": "'\\x6B\\x4A\\x79\\xF6\\xD6\\xDF\\x9B\\xD5...' (32 bytes = 64 hex chars)"},
}

TRANSFORM_KEYS = list(TRANSFORMS.keys())

SAMPLE_PROFILES_DIR = Path("client/user/profiles")


# ════════════════════════════════════════════════════════════════════════════
#  DATA MODEL — single source of truth for all GUI state
# ════════════════════════════════════════════════════════════════════════════

def _empty_model() -> dict:
    return {
        "name": "My Custom Profile",
        "author": "",
        "proto": "tcp",
        "get": {
            "body": "<METADATA>",
            "client_transforms": [],
            "server_body": "<OUTPUT>",
            "server_transforms": [],
        },
        "post": {
            "body": "<OUTPUT>",
            "client_transforms": [],
            "server_body": "",
        },
    }


profile_model: dict = _empty_model()

# Generated TOML for right panel
toml_text: dict = {"value": "# Click 'Build Profile' to generate TOML"}

# UI element refs populated during render — keyed for access from build/extract
# These are set by the @ui.refreshable and read by build_toml / sync_model_from_ui
ui_refs: dict = {}


# ════════════════════════════════════════════════════════════════════════════
#  TOML PARSING (file → model)
# ════════════════════════════════════════════════════════════════════════════

def _normalize_transform(t: dict) -> dict:
    """Normalize a parsed TOML transform entry to {op, val}."""
    op = t.get("op", "")
    val = t.get("val", "") or t.get("key", "")
    entry = {"op": op}
    if val:
        entry["val"] = val
    return entry


def _body_to_textarea(body: str) -> str:
    """Convert a parsed TOML body string for textarea display.

    TOML basic strings turn \\r\\n into real CR+LF during parsing.
    The textarea shows these as actual newlines, which is natural for editing.
    The build step converts them back to \\r\\n in the TOML output.
    """
    return body


def parse_toml(toml_str: str) -> dict:
    """Parse a TOML profile string into a profile_model dict."""
    data = tomllib.loads(toml_str)
    model = _empty_model()

    # [profile]
    prof = data.get("profile", {})
    model["name"] = prof.get("name", "Untitled Profile")
    model["author"] = prof.get("author", "")

    raw = data.get("raw", {})

    # [raw.get]
    get = raw.get("get", {})
    model["proto"] = get.get("proto", raw.get("post", {}).get("proto", "tcp"))
    model["get"]["body"] = _body_to_textarea(get.get("body", "<METADATA>"))

    # [raw.get.client.metadata] transforms
    client_meta = get.get("client", {}).get("metadata", {})
    model["get"]["client_transforms"] = [
        _normalize_transform(t) for t in client_meta.get("transforms", [])
    ]

    # [raw.get.server]
    server_get = get.get("server", {})
    model["get"]["server_body"] = _body_to_textarea(server_get.get("body", "<OUTPUT>"))

    # [raw.get.server.output] transforms
    server_output = server_get.get("output", {})
    model["get"]["server_transforms"] = [
        _normalize_transform(t) for t in server_output.get("transforms", [])
    ]

    # [raw.post]
    post = raw.get("post", {})
    model["post"]["body"] = _body_to_textarea(post.get("body", "<OUTPUT>"))

    # [raw.post.client.output] transforms
    client_output = post.get("client", {}).get("output", {})
    model["post"]["client_transforms"] = [
        _normalize_transform(t) for t in client_output.get("transforms", [])
    ]

    # [raw.post.server]
    server_post = post.get("server", {})
    model["post"]["server_body"] = _body_to_textarea(server_post.get("body", ""))

    return model


# ════════════════════════════════════════════════════════════════════════════
#  TOML GENERATION (model → TOML string)
# ════════════════════════════════════════════════════════════════════════════

def _format_transform_val(op: str, val: str) -> str:
    field = TRANSFORMS.get(op, {}).get("field")
    if not field or not val:
        return ""
    return f", {field} = '{val}'"


def _format_transforms_list(transforms: list[dict]) -> str:
    if not transforms:
        return "transforms = []"
    lines = ["transforms = ["]
    for i, t in enumerate(transforms):
        op = t["op"]
        val_part = _format_transform_val(op, t.get("val", ""))
        comma = "," if i < len(transforms) - 1 else ""
        lines.append(f'    {{ op = "{op}"{val_part} }}{comma}')
    lines.append("]")
    return "\n".join(lines)


def _escape_toml_body(text: str) -> str:
    r"""Escape a body string for TOML basic string (double-quoted).

    Handles:
    - Real newlines (from textarea Enter key) → \r\n
    - User-typed literal \r\n, \xNN → preserved as-is
    - Quotes → escaped
    - Stray backslashes → escaped
    """
    SENTINEL = "\x00ESC\x00"
    escapes = []

    def _protect(m):
        escapes.append(m.group(0))
        return f"{SENTINEL}{len(escapes) - 1}{SENTINEL}"

    text = re.sub(r'\\x[0-9A-Fa-f]{2}|\\r|\\n', _protect, text)

    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')

    text = text.replace("\r\n", "\\r\\n")
    text = text.replace("\r", "\\r\\n")
    text = text.replace("\n", "\\r\\n")

    for i, esc in enumerate(escapes):
        text = text.replace(f"{SENTINEL}{i}{SENTINEL}", esc)

    return text


def sync_model_from_ui():
    """Pull current UI values into profile_model before building TOML.

    The model was used to populate the UI initially, but the user may have
    edited fields since. This syncs those edits back into the model.
    """
    refs = ui_refs

    if "name" in refs:
        profile_model["name"] = refs["name"].value or "Untitled Profile"
    if "author" in refs:
        profile_model["author"] = refs["author"].value or ""
    if "proto" in refs:
        profile_model["proto"] = refs["proto"].value or "tcp"

    for chain in ("get", "post"):
        body_ref = refs.get(f"{chain}_body")
        if body_ref:
            profile_model[chain]["body"] = body_ref.value or ""

        server_body_ref = refs.get(f"{chain}_server_body")
        if server_body_ref:
            profile_model[chain]["server_body"] = server_body_ref.value or ""

        # Extract transforms from card children (preserves drag order)
        card = refs.get(f"{chain}_client_card")
        if card:
            profile_model[chain]["client_transforms"] = _extract_card_transforms(card)

        if chain == "get":
            server_card = refs.get(f"{chain}_server_card")
            if server_card:
                profile_model[chain]["server_transforms"] = _extract_card_transforms(server_card)


def _extract_card_transforms(card) -> list[dict]:
    result = []
    for child in card.default_slot.children:
        op = child.transform_op.value
        val = child.transform_val.value if hasattr(child, "transform_val") else ""
        entry = {"op": op}
        if val:
            entry["val"] = val
        result.append(entry)
    return result


def build_toml() -> str:
    """Build TOML from profile_model."""
    m = profile_model
    lines = []

    lines.append("[profile]")
    lines.append(f'name = "{_escape_toml_body(m["name"])}"')
    if m["author"]:
        lines.append(f'author = "{_escape_toml_body(m["author"])}"')
    lines.append("")

    # GET
    lines.append("[raw.get]")
    lines.append(f'proto = "{m["proto"]}"')
    lines.append(f'body = "{_escape_toml_body(m["get"]["body"])}"')
    lines.append("")

    lines.append("[raw.get.client.metadata]")
    lines.append(_format_transforms_list(m["get"]["client_transforms"]))
    lines.append("")

    lines.append("[raw.get.server]")
    lines.append(f'body = "{_escape_toml_body(m["get"]["server_body"])}"')
    lines.append("")

    lines.append("[raw.get.server.output]")
    lines.append(_format_transforms_list(m["get"]["server_transforms"]))
    lines.append("")

    # POST
    lines.append("[raw.post]")
    lines.append(f'proto = "{m["proto"]}"')
    lines.append(f'body = "{_escape_toml_body(m["post"]["body"])}"')
    lines.append("")

    lines.append("[raw.post.client.output]")
    lines.append(_format_transforms_list(m["post"]["client_transforms"]))
    lines.append("")

    lines.append("[raw.post.server]")
    lines.append(f'body = "{_escape_toml_body(m["post"]["server_body"])}"')

    return "\n".join(lines)


def do_build():
    sync_model_from_ui()
    toml_text["value"] = build_toml()
    preview_panel.refresh()


# ════════════════════════════════════════════════════════════════════════════
#  LOAD / NEW PROFILE ACTIONS
# ════════════════════════════════════════════════════════════════════════════

def do_new():
    """Reset to a blank profile."""
    global profile_model
    profile_model = _empty_model()
    toml_text["value"] = "# Click 'Build Profile' to generate TOML"
    editor_panel.refresh()
    preview_panel.refresh()


def do_load_text(toml_str: str):
    """Parse TOML text and load into the editor."""
    global profile_model
    try:
        profile_model = parse_toml(toml_str)
    except Exception as e:
        ui.notify(f"TOML parse error: {e}", type="negative", position="top")
        return
    toml_text["value"] = "# Loaded — click 'Build Profile' to regenerate"
    editor_panel.refresh()
    preview_panel.refresh()
    ui.notify(f"Loaded profile: {profile_model['name']}", type="positive", position="top")


def do_load_file(e: events.UploadEventArguments):
    """Handle file upload."""
    try:
        content = e.content.read().decode("utf-8")
    except Exception as ex:
        ui.notify(f"File read error: {ex}", type="negative", position="top")
        return
    do_load_text(content)


def show_load_dialog():
    """Show dialog with sample profile picker, file upload, and paste area."""
    with ui.dialog().props("maximized=false") as dialog, \
         ui.card().classes("w-[600px]").style("max-height: 80vh;"):

        ui.label("Load Profile").classes("text-lg font-bold")

        # Sample profiles from disk
        sample_files = sorted(SAMPLE_PROFILES_DIR.glob("raw_*.toml")) if SAMPLE_PROFILES_DIR.exists() else []
        if sample_files:
            ui.label("Load a built-in profile:").classes("text-sm text-gray-400 mt-2")
            with ui.row().classes("w-full flex-wrap gap-2"):
                for f in sample_files:
                    stem = f.stem.replace("raw_", "").replace("_profile", "").replace("_", " ").title()

                    def _load_sample(path=f):
                        do_load_text(path.read_text())
                        dialog.close()

                    ui.button(stem, on_click=_load_sample).props("outline dense size=sm")

        ui.separator().classes("my-2")

        # File upload
        ui.label("Upload a .toml file:").classes("text-sm text-gray-400")

        def _on_upload(e: events.UploadEventArguments):
            do_load_file(e)
            dialog.close()

        ui.upload(
            label="Choose .toml file",
            auto_upload=True,
            on_upload=_on_upload,
        ).props('accept=".toml" flat bordered').classes("w-full")

        ui.separator().classes("my-2")

        # Paste area
        ui.label("Or paste TOML directly:").classes("text-sm text-gray-400")
        paste_area = ui.textarea(placeholder="Paste TOML here...").classes(
            "w-full font-mono"
        ).props("autogrow rows=6")

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")

            def _load_pasted():
                if paste_area.value and paste_area.value.strip():
                    do_load_text(paste_area.value)
                    dialog.close()

            ui.button("Load", on_click=_load_pasted, color="amber-9").props("unelevated")

    dialog.open()


# ════════════════════════════════════════════════════════════════════════════
#  TRANSFORM CHAIN UI
# ════════════════════════════════════════════════════════════════════════════

def _wire_badge(label: str, color: str = "grey-8") -> ui.badge:
    return ui.badge(label, color=color).props("outline dense").classes("text-[10px]")


def _render_wire_flow(container, info: dict):
    """Render wire flow badges into a container (clears first)."""
    container.clear()
    with container:
        with ui.row().classes("items-center gap-1"):
            ui.label("Wire:").classes("text-[10px] text-gray-600")
            _wire_badge(info.get("wire_in", "any"), "blue-grey-7")
            ui.icon("arrow_forward", size="xs").classes("text-gray-600")
            _wire_badge(info.get("wire_out", "any"), "teal-8")


def add_transform(card: ui.card, op: str = "base64", val: str = ""):
    """Add a draggable transform entry to a card, optionally pre-populated."""
    info = TRANSFORMS.get(op, TRANSFORMS["base64"])
    needs_input = info.get("input", False)

    with card:
        with ui.expansion(text=op).classes("w-full") as expansion:
            with expansion.add_slot("header"):
                with ui.row().classes("items-center gap-2 w-full"):
                    ui.icon("drag_indicator").classes(
                        "drag-handle cursor-grab active:cursor-grabbing text-gray-400"
                    )
                    expansion_label = ui.label(op).style("font-weight: 500")

            expansion.transform_op = ui.select(
                TRANSFORM_KEYS,
                value=op,
                label="Operation",
                on_change=lambda: _on_transform_change(
                    expansion, expansion_label, wire_flow_container,
                    val_hint_label, val_example_label,
                ),
            ).classes("w-full")

            expansion.transform_desc = ui.label(info.get("desc", "")).classes(
                "text-xs text-gray-500"
            )

            wire_flow_container = ui.column().classes("w-full gap-0")
            _render_wire_flow(wire_flow_container, info)

            field = info.get("field", "val")
            if field == "key":
                lbl = 'Key — raw bytes as \\xNN hex escapes'
                ph = '\\x6B\\x4A\\x79\\xF6...'
            else:
                lbl = 'Value — text or \\xNN hex bytes'
                ph = '\\x0D\\x0A or plain text'

            expansion.transform_val = ui.input(
                label=lbl,
                value=val,
                placeholder=ph,
            ).classes("w-full font-mono")
            expansion.transform_val.set_visibility(needs_input)

            val_hint_label = ui.label(info.get("val_hint", "")).classes("text-[11px] text-amber-400")
            val_hint_label.set_visibility(needs_input)
            val_example_label = ui.label(info.get("val_example", "")).classes(
                "text-[10px] text-gray-500 font-mono"
            )
            val_example_label.set_visibility(needs_input)

            ui.button(
                "Delete", icon="delete", color="red-9",
                on_click=lambda e, exp=expansion: exp.delete(),
            ).props("flat dense")


def _on_transform_change(expansion, label, wire_flow_container, val_hint_label, val_example_label):
    op = expansion.transform_op.value
    label.set_text(op)

    info = TRANSFORMS.get(op, {})
    needs_input = info.get("input", False)
    expansion.transform_val.set_visibility(needs_input)
    val_hint_label.set_visibility(needs_input)
    val_example_label.set_visibility(needs_input)
    if not needs_input:
        expansion.transform_val.set_value("")

    field = info.get("field", "val")
    if field == "key":
        expansion.transform_val.props(
            'label="Key — raw bytes as \\\\xNN hex escapes"'
            ' placeholder="\\x6B\\x4A\\x79\\xF6..."'
        )
    else:
        expansion.transform_val.props(
            'label="Value — text or \\\\xNN hex bytes"'
            ' placeholder="\\x0D\\x0A or plain text"'
        )

    expansion.transform_desc.set_text(info.get("desc", ""))
    val_hint_label.set_text(info.get("val_hint", ""))
    val_example_label.set_text(info.get("val_example", ""))

    _render_wire_flow(wire_flow_container, info)


def transform_chain_editor(chain: str, sub_chain: str):
    """Render a transform chain editor, pre-populated from profile_model."""
    with ui.column().classes("w-full gap-2"):
        card = ui.card().classes("w-full min-h-[60px]").style(
            "border: 1px dashed #444; background: transparent; padding: 8px;"
        )

        # Register in ui_refs for sync_model_from_ui
        ui_refs[f"{chain}_{sub_chain}_card"] = card

        # Pre-populate from model
        if sub_chain == "client":
            transforms = profile_model[chain].get("client_transforms", [])
        else:
            transforms = profile_model[chain].get("server_transforms", [])

        for t in transforms:
            add_transform(card, op=t["op"], val=t.get("val", ""))

        # make_sortable AFTER children are added — SortableJS must see
        # existing children when it initializes, otherwise drag handles
        # on pre-populated items don't bind.
        card.make_sortable(handle=".drag-handle")

        ui.button(
            "Add Transform", icon="add",
            on_click=lambda _e=None, c=card: add_transform(c),
        ).props("outline dense").classes("w-full")


# ════════════════════════════════════════════════════════════════════════════
#  LEFT PANEL — EDITOR (refreshable)
# ════════════════════════════════════════════════════════════════════════════

def _body_hint_block():
    """Shared hint block shown below body textareas."""
    with ui.column().classes("gap-0 -mt-2").style(
        "border-left: 2px solid #5c4d8a; padding-left: 8px;"
    ):
        ui.label(
            "This is a text template. Everything here goes on the wire as "
            "literal bytes — what you type is what gets sent."
        ).classes("text-[11px] text-gray-400")
        ui.html(
            '<span style="color:#b0b0b0;font-size:11px;">'
            'The only substitutions are tokens: '
            '<code style="color:#80cbc4;">&lt;METADATA&gt;</code>, '
            '<code style="color:#80cbc4;">&lt;OUTPUT&gt;</code>, '
            '<code style="color:#80cbc4;">&lt;CLIENT_ID&gt;</code>. '
            'Tokens are replaced with the <em>transformed</em> payload data. '
            'Everything else is literal.</span>'
        )
        ui.html(
            '<div style="font-size:11px;color:#ffcc80;margin-top:2px;">'
            '<b>Newlines:</b> You can type/paste multi-line text here (e.g. HTTP headers). '
            'Each newline becomes <code>\\r\\n</code> (CR LF) in the TOML output. '
            'You can also type <code>\\r\\n</code> literally if you prefer single-line entry.'
            '</div>'
        )
        ui.html(
            '<div style="font-size:11px;color:#b0b0b0;margin-top:2px;">'
            '<b>Hex bytes:</b> Use <code>\\xNN</code> for raw byte values '
            '(e.g. <code>\\x00</code> for null). These are preserved as-is in the TOML output.'
            '</div>'
        )


def chain_panel(chain: str):
    """Editor for one chain (get or post), reading initial values from profile_model."""
    m = profile_model[chain]
    is_get = chain == "get"
    client_token = "<METADATA>" if is_get else "<OUTPUT>"
    client_section_name = "client.metadata" if is_get else "client.output"

    with ui.column().classes("w-full gap-4 p-2"):

        # Body template
        with ui.row().classes("items-center gap-2"):
            ui.label("Body Template (client → server)").classes(
                "text-sm font-bold text-gray-300"
            )
            _wire_badge("TEXT TEMPLATE", "deep-purple-8")

        body_input = ui.textarea(
            label=f"[raw.{chain}] body",
            value=m["body"],
            placeholder=client_token,
        ).classes("w-full font-mono").props("autogrow rows=2")
        ui_refs[f"{chain}_body"] = body_input

        _body_hint_block()
        ui.separator()

        # Sub-tabs: REQ / RESP
        with ui.tabs().classes("w-full").props("dense active-color=teal") as sub_tabs:
            req_tab = ui.tab("REQ (to server)")
            resp_tab = ui.tab("RESP (from server)")

        with ui.tab_panels(sub_tabs, value=req_tab).classes("w-full"):
            with ui.tab_panel(req_tab):
                ui.label(f"Transforms for [{client_section_name}]").classes(
                    "text-xs text-gray-500 mb-1"
                )
                transform_chain_editor(chain, "client")

            with ui.tab_panel(resp_tab):
                with ui.row().classes("items-center gap-2"):
                    ui.label("Server Response Body").classes(
                        "text-sm font-bold text-gray-300"
                    )
                    _wire_badge("TEXT TEMPLATE", "deep-purple-8")

                server_default = m.get("server_body", "<OUTPUT>" if is_get else "")
                server_ph = "<OUTPUT>" if is_get else "HTTP/1.1 200 OK\\r\\n\\r\\n"

                server_body_input = ui.textarea(
                    label=f"[raw.{chain}.server] body",
                    value=server_default,
                    placeholder=server_ph,
                ).classes("w-full font-mono").props("autogrow rows=2")
                ui_refs[f"{chain}_server_body"] = server_body_input

                if is_get:
                    ui.label(
                        "Server response template. <OUTPUT> is replaced with transformed "
                        "task data. Surrounding text is sent as literal bytes."
                    ).classes("text-[11px] text-gray-500 -mt-2")
                    ui.separator().classes("my-2")
                    ui.label("Transforms for [server.output]").classes(
                        "text-xs text-gray-500 mb-1"
                    )
                    transform_chain_editor(chain, "server")
                else:
                    with ui.column().classes("gap-1 mt-1").style(
                        "border-left: 2px solid #5c4d8a; padding-left: 8px;"
                    ):
                        ui.label(
                            "POST server body is the ACK sent back to the implant. "
                            "No transforms — this string is sent on the wire exactly as-is."
                        ).classes("text-[11px] text-gray-500")
                        ui.label(
                            "Leave empty for fire-and-forget (e.g. NTP, DNS). "
                            "Set to 'HTTP/1.1 200 OK\\r\\n\\r\\n' for HTTP ACK."
                        ).classes("text-[11px] text-gray-500")


def options_panel():
    m = profile_model
    with ui.column().classes("w-full gap-4 p-4"):
        ui.label("Profile Settings").classes("text-lg font-bold text-gray-200")

        name_input = ui.input(
            label="Profile Name", value=m["name"],
            placeholder="e.g. HTTP Mimicry",
        ).classes("w-full")
        ui_refs["name"] = name_input

        author_input = ui.input(
            label="Author", value=m["author"],
            placeholder="e.g. operator handle",
        ).classes("w-full")
        ui_refs["author"] = author_input

        proto_toggle = ui.toggle(["tcp", "udp"], value=m["proto"]).classes("w-full")
        ui_refs["proto"] = proto_toggle

        ui.separator()

        with ui.column().classes("gap-2"):
            ui.label("Quick Reference").classes("text-sm font-bold text-gray-400")
            ui.label("TCP — one message per connection (HTTP, FTP, etc.)").classes("text-xs text-gray-500")
            ui.label("UDP — one datagram per transaction (NTP, DNS, SNMP)").classes("text-xs text-gray-500")
            ui.label("~64KB hard limit on UDP datagrams after transform expansion").classes("text-xs text-gray-500")

        ui.separator()

        ui.label("Available Tokens").classes("text-sm font-bold text-gray-400")
        for token, desc in [
            ("<METADATA>", "Encoded beacon metadata (GET body)"),
            ("<OUTPUT>", "Encoded exfil data / tasks (POST body, server responses)"),
            ("<CLIENT_ID>", "Implant UUID (optional, POST body)"),
        ]:
            with ui.row().classes("items-center gap-2"):
                ui.badge(token, color="teal-9").props("outline")
                ui.label(desc).classes("text-xs text-gray-500")

        ui.separator()

        # Text vs Bytes reference
        ui.label("Text vs Bytes Reference").classes("text-sm font-bold text-gray-400")
        with ui.column().classes("gap-3"):

            with ui.card().classes("w-full").style(
                "background: #1e2a3a; border: 1px solid #2a4060; padding: 12px;"
            ):
                with ui.row().classes("items-center gap-2 mb-1"):
                    _wire_badge("TEXT TEMPLATE", "deep-purple-8")
                    ui.label("Body Fields").classes("text-xs font-bold text-gray-300")
                ui.label(
                    "Body is a text template that defines the packet structure. "
                    "Everything you type goes on the wire as literal bytes. "
                    "Only the three tokens (<METADATA>, <OUTPUT>, <CLIENT_ID>) "
                    "get replaced — everything else is sent exactly as written."
                ).classes("text-[11px] text-gray-400")
                ui.html(
                    '<div style="font-family:monospace;font-size:11px;color:#a0c4ff;margin-top:4px;">'
                    'body = "GET /api?d=&lt;METADATA&gt; HTTP/1.1\\r\\n\\r\\n"<br>'
                    '<span style="color:#666;">      ^^^^^^^^^^^^^^^^  literal text on wire</span><br>'
                    '<span style="color:#80cbc4;">                     ^^^^^^^^^^  replaced with transformed data</span><br>'
                    '<span style="color:#666;">                                  ^^^^^^^^^^^^^^^^^^^^  literal text</span>'
                    '</div>'
                )

            with ui.card().classes("w-full").style(
                "background: #1e2a3a; border: 1px solid #2a4060; padding: 12px;"
            ):
                with ui.row().classes("items-center gap-2 mb-1"):
                    _wire_badge("\\xNN BYTES", "teal-8")
                    ui.label("Transform val / key Fields").classes("text-xs font-bold text-gray-300")
                ui.label(
                    "Transform values use \\xNN hex escapes for raw bytes. "
                    "The server converts each \\xNN to the corresponding byte at runtime. "
                    "Plain ASCII characters (letters, digits, punctuation) go as-is."
                ).classes("text-[11px] text-gray-400")
                ui.html(
                    '<div style="font-family:monospace;font-size:11px;margin-top:4px;">'
                    '<span style="color:#ffcc80;">\\x23</span>'
                    '<span style="color:#888;"> → byte 0x23 (one byte, value 35)</span><br>'
                    '<span style="color:#ffcc80;">GET /</span>'
                    '<span style="color:#888;"> → five ASCII bytes: G E T space /</span><br>'
                    '<span style="color:#ffcc80;">GET /\\x0D\\x0A</span>'
                    '<span style="color:#888;"> → "GET /" + CR + LF (7 bytes total)</span>'
                    '</div>'
                )
                ui.separator().classes("my-2")
                ui.html(
                    '<div style="font-size:11px;">'
                    '<span style="color:#ef5350;font-weight:bold;">Common mistake:</span> '
                    '<span style="color:#ef9a9a;">typing <code>0D0A</code> instead of '
                    '<code>\\x0D\\x0A</code> sends the four ASCII characters "0D0A", '
                    'not a CR LF. Always use the \\xNN prefix for byte values.</span>'
                    '</div>'
                )

            with ui.card().classes("w-full").style(
                "background: #1e2a3a; border: 1px solid #2a4060; padding: 12px;"
            ):
                with ui.row().classes("items-center gap-2 mb-1"):
                    ui.icon("swap_horiz", size="xs").classes("text-amber-400")
                    ui.label("Transform Data Flow").classes("text-xs font-bold text-gray-300")
                ui.html(
                    '<div style="font-size:11px;color:#b0b0b0;line-height:1.6;">'
                    '1. Raw payload starts as <b style="color:#90caf9;">binary msgpack bytes</b><br>'
                    '2. Each transform runs <b>in order, top to bottom</b><br>'
                    '3. Output of one transform feeds into the next<br>'
                    '4. Final result replaces the token in the body template<br>'
                    '5. Body template + replaced token = <b style="color:#a5d6a7;">bytes on the wire</b>'
                    '</div>'
                )
                ui.html(
                    '<div style="font-family:monospace;font-size:10px;color:#888;'
                    'margin-top:6px;background:#141e2b;padding:6px;border-radius:4px;">'
                    'msgpack bytes<br>'
                    '  → symcrypt  → <span style="color:#ef9a9a;">encrypted bytes</span> (+28B overhead)<br>'
                    '  → base64   → <span style="color:#a5d6a7;">ASCII text</span> (~1.33x larger)<br>'
                    '  → prepend  → <span style="color:#ffcc80;">val bytes</span> + ASCII text<br>'
                    '  → replaces &lt;TOKEN&gt; in body template<br>'
                    '  = final wire packet'
                    '</div>'
                )


@ui.refreshable
def editor_panel():
    """The full left-side editor — rebuilt from profile_model on load."""
    # Clear UI refs on each refresh so stale elements don't persist
    ui_refs.clear()

    with ui.column().classes("w-full h-full"):
        with ui.tabs().classes("w-full").props("dense active-color=amber") as main_tabs:
            get_tab = ui.tab("GET")
            post_tab = ui.tab("POST")
            opts_tab = ui.tab("OPTIONS")

        with ui.tab_panels(main_tabs, value=get_tab).classes("w-full flex-grow"):
            with ui.tab_panel(get_tab):
                chain_panel("get")
            with ui.tab_panel(post_tab):
                chain_panel("post")
            with ui.tab_panel(opts_tab):
                options_panel()

        ui.button(
            "Build Profile", icon="build", color="amber-9",
            on_click=do_build,
        ).classes("w-full mt-2").props("unelevated")


# ════════════════════════════════════════════════════════════════════════════
#  RIGHT PANEL — PREVIEW
# ════════════════════════════════════════════════════════════════════════════

@ui.refreshable
def preview_panel():
    with ui.column().classes("w-full h-full"):
        with ui.tabs().classes("w-full").props("dense active-color=cyan") as preview_tabs:
            rendered_tab = ui.tab("Rendered")
            raw_tab = ui.tab("Raw")

        with ui.tab_panels(preview_tabs, value=raw_tab).classes("w-full flex-grow"):
            with ui.tab_panel(rendered_tab):
                with ui.column().classes("w-full h-full items-center justify-center gap-4"):
                    ui.icon("visibility", size="xl").classes("text-gray-600")
                    ui.label("Rendered preview coming soon").classes("text-gray-500 text-sm")

            with ui.tab_panel(raw_tab):
                ui.codemirror(
                    toml_text["value"],
                    language="TOML",
                    theme="androidstudio",
                ).classes("w-full h-full min-h-[500px]").props("readonly")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE
# ════════════════════════════════════════════════════════════════════════════

@ui.page("/")
def page():
    ui.dark_mode(True)
    ui.query("body").style("margin: 0; padding: 0;")
    ui.query(".nicegui-content").classes("h-screen").style("padding: 0;")

    # Header bar
    with ui.row().classes("w-full items-center px-4 py-2 gap-2").style(
        "background: #1a1a2e; border-bottom: 1px solid #333;"
    ):
        ui.icon("router", size="sm").classes("text-amber-400")
        ui.label("Profile Builder").classes("text-lg font-bold text-gray-200")
        ui.label("POC v3").classes("text-xs text-gray-500")

        ui.space()

        ui.button("New", icon="note_add", on_click=do_new).props(
            "flat dense size=sm text-color=grey-5"
        )
        ui.button("Load", icon="folder_open", on_click=show_load_dialog).props(
            "flat dense size=sm text-color=grey-5"
        )

    # Splitter: editor | preview
    with ui.splitter(value=50).classes("w-full flex-grow").style(
        "height: calc(100vh - 48px);"
    ) as splitter:
        with splitter.before:
            with ui.scroll_area().classes("h-full"):
                editor_panel()

        with splitter.after:
            with ui.scroll_area().classes("h-full"):
                preview_panel()


ui.run(port=8090, title="Profile Builder", reload=True)
