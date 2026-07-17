from nicegui import ui


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

# ── Shared state ────────────────────────────────────────────────────────────
# Card refs keyed by (chain, sub_chain) — e.g. ("get", "client"), ("post", "server")
transform_cards: dict[tuple[str, str], ui.card] = {}

# Body template inputs keyed by (chain, sub_chain) — e.g. ("get", "main"), ("get", "server")
body_inputs: dict[tuple[str, str], ui.input | ui.textarea] = {}

# Options inputs
option_inputs: dict[str, object] = {}

# Generated TOML text for the right panel
toml_text: dict = {"value": "# Click 'Build Profile' to generate TOML"}


# ════════════════════════════════════════════════════════════════════════════
#  TOML GENERATION
# ════════════════════════════════════════════════════════════════════════════

def _format_transform_val(op: str, val: str) -> str:
    """Format a single transform value field for TOML inline table output.

    Uses single-quoted literal strings (required for \\xNN hex escapes).
    """
    field = TRANSFORMS.get(op, {}).get("field")
    if not field or not val:
        return ""
    return f", {field} = '{val}'"


def _format_transforms_list(transforms: list[dict]) -> str:
    """Render a transforms list as a TOML array-of-inline-tables."""
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
    r"""Escape a body template string for TOML basic string (double-quoted).

    The textarea may contain:
    - Real newlines from Enter key → converted to \r\n on the wire
    - User-typed literal \r\n sequences → preserved as-is
    - User-typed \xNN hex escapes → preserved as-is
    - Quotes → escaped for TOML

    We first protect user-typed escape sequences from being double-escaped,
    then convert real newlines to \r\n for wire correctness.
    """
    # Protect user-typed backslash sequences by using a sentinel
    # Split on \x (hex escapes) and \r \n (literal typed escapes) to preserve them
    import re
    # Extract user-typed escape sequences and protect them
    SENTINEL = "\x00ESCSEQ\x00"
    escapes = []

    def _protect(m):
        escapes.append(m.group(0))
        return f"{SENTINEL}{len(escapes) - 1}{SENTINEL}"

    # Protect \xNN, \r, \n that the user typed literally (as two chars: \ then x/r/n)
    text = re.sub(r'\\x[0-9A-Fa-f]{2}|\\r|\\n', _protect, text)

    # Now escape remaining backslashes and quotes for TOML
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')

    # Convert real newlines (from textarea Enter key) to \r\n
    text = text.replace("\r\n", "\\r\\n")
    text = text.replace("\r", "\\r\\n")
    text = text.replace("\n", "\\r\\n")

    # Restore protected escape sequences
    for i, esc in enumerate(escapes):
        text = text.replace(f"{SENTINEL}{i}{SENTINEL}", esc)

    return text


def extract_transforms(chain: str, sub_chain: str) -> list[dict]:
    """Pull the current ordered transforms from a card's children."""
    card = transform_cards.get((chain, sub_chain))
    if not card:
        return []
    result = []
    for child in card.default_slot.children:
        op = child.transform_op.value
        val = child.transform_val.value if hasattr(child, "transform_val") else ""
        entry = {"op": op}
        if val:
            entry["val"] = val
        result.append(entry)
    return result


def get_body(chain: str, sub_chain: str) -> str:
    """Get body template text from the corresponding input."""
    inp = body_inputs.get((chain, sub_chain))
    if inp is None:
        return ""
    return inp.value or ""


def build_toml() -> str:
    """Assemble the full raw profile TOML from all GUI state."""
    name = option_inputs.get("name")
    author = option_inputs.get("author")
    proto = option_inputs.get("proto")

    profile_name = name.value if name else "Untitled Profile"
    profile_author = author.value if author else ""
    profile_proto = proto.value if proto else "tcp"

    lines = []

    # [profile]
    lines.append("[profile]")
    lines.append(f'name = "{_escape_toml_body(profile_name)}"')
    if profile_author:
        lines.append(f'author = "{_escape_toml_body(profile_author)}"')
    lines.append("")

    # ── GET ──────────────────────────────────────────────────────────────
    get_body_val = get_body("get", "main")
    lines.append("[raw.get]")
    lines.append(f'proto = "{profile_proto}"')
    lines.append(f'body = "{_escape_toml_body(get_body_val)}"')
    lines.append("")

    # [raw.get.client.metadata]
    get_client_transforms = extract_transforms("get", "client")
    lines.append("[raw.get.client.metadata]")
    lines.append(_format_transforms_list(get_client_transforms))
    lines.append("")

    # [raw.get.server]
    get_server_body = get_body("get", "server")
    lines.append("[raw.get.server]")
    lines.append(f'body = "{_escape_toml_body(get_server_body)}"')
    lines.append("")

    # [raw.get.server.output]
    get_server_transforms = extract_transforms("get", "server")
    lines.append("[raw.get.server.output]")
    lines.append(_format_transforms_list(get_server_transforms))
    lines.append("")

    # ── POST ─────────────────────────────────────────────────────────────
    post_body_val = get_body("post", "main")
    lines.append("[raw.post]")
    lines.append(f'proto = "{profile_proto}"')
    lines.append(f'body = "{_escape_toml_body(post_body_val)}"')
    lines.append("")

    # [raw.post.client.output]
    post_client_transforms = extract_transforms("post", "client")
    lines.append("[raw.post.client.output]")
    lines.append(_format_transforms_list(post_client_transforms))
    lines.append("")

    # [raw.post.server]
    post_server_body = get_body("post", "server")
    lines.append("[raw.post.server]")
    lines.append(f'body = "{_escape_toml_body(post_server_body)}"')

    return "\n".join(lines)


def do_build():
    """Build profile and refresh the preview panel."""
    toml_text["value"] = build_toml()
    preview_panel.refresh()


# ════════════════════════════════════════════════════════════════════════════
#  TRANSFORM CHAIN UI
# ════════════════════════════════════════════════════════════════════════════

def _wire_badge(label: str, color: str = "grey-8") -> ui.badge:
    """Small inline badge for data-type indicators."""
    return ui.badge(label, color=color).props("outline dense").classes("text-[10px]")


def _build_wire_flow(info: dict) -> ui.row:
    """Build a row showing: [input type] -> OP -> [output type]."""
    with ui.row().classes("items-center gap-1 mt-1") as row:
        _wire_badge(info.get("wire_in", "any"), "blue-grey-7")
        ui.icon("arrow_forward", size="xs").classes("text-gray-600")
        _wire_badge(info.get("wire_out", "any"), "teal-8")
    return row


def add_transform(card: ui.card):
    """Add a new draggable transform entry to a card."""
    with card:
        with ui.expansion(text="base64").classes("w-full") as expansion:
            with expansion.add_slot("header"):
                with ui.row().classes("items-center gap-2 w-full"):
                    ui.icon("drag_indicator").classes(
                        "drag-handle cursor-grab active:cursor-grabbing text-gray-400"
                    )
                    expansion_label = ui.label("base64").style("font-weight: 500")

            expansion.transform_op = ui.select(
                TRANSFORM_KEYS,
                value="base64",
                label="Operation",
                on_change=lambda: _on_transform_change(
                    expansion, expansion_label, wire_flow_container, val_hint_label, val_example_label,
                ),
            ).classes("w-full")

            target = TRANSFORMS.get("base64", {})
            expansion.transform_desc = ui.label(target.get("desc", "")).classes(
                "text-xs text-gray-500"
            )

            wire_flow_container = ui.column().classes("w-full gap-0")
            with wire_flow_container:
                with ui.row().classes("items-center gap-1"):
                    ui.label("Wire:").classes("text-[10px] text-gray-600")
                    _wire_badge(target.get("wire_in", "any"), "blue-grey-7")
                    ui.icon("arrow_forward", size="xs").classes("text-gray-600")
                    _wire_badge(target.get("wire_out", "any"), "teal-8")

            expansion.transform_val = ui.input(
                label="Value",
                placeholder="e.g. \\x0D\\x0A or plaintext",
            ).classes("w-full font-mono")
            expansion.transform_val.set_visibility(False)

            val_hint_label = ui.label("").classes("text-[11px] text-amber-400")
            val_hint_label.set_visibility(False)
            val_example_label = ui.label("").classes(
                "text-[10px] text-gray-500 font-mono"
            )
            val_example_label.set_visibility(False)

            ui.button(
                "Delete",
                icon="delete",
                color="red-9",
                on_click=lambda e, exp=expansion: exp.delete(),
            ).props("flat dense")


def _on_transform_change(expansion, label, wire_flow_container, val_hint_label, val_example_label):
    """React to a transform op dropdown change."""
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

    wire_flow_container.clear()
    with wire_flow_container:
        with ui.row().classes("items-center gap-1"):
            ui.label("Wire:").classes("text-[10px] text-gray-600")
            _wire_badge(info.get("wire_in", "any"), "blue-grey-7")
            ui.icon("arrow_forward", size="xs").classes("text-gray-600")
            _wire_badge(info.get("wire_out", "any"), "teal-8")


def transform_chain_editor(chain: str, sub_chain: str):
    """Render a transform chain editor (add button + sortable card)."""
    with ui.column().classes("w-full gap-2"):
        ui.button(
            "Add Transform",
            icon="add",
            on_click=lambda: add_transform(card),
        ).props("outline dense").classes("w-full")

        card = ui.card().classes("w-full min-h-[80px]").style(
            "border: 1px dashed #444; background: transparent; padding: 8px;"
        )
        card.make_sortable(handle=".drag-handle")
        transform_cards[(chain, sub_chain)] = card


# ════════════════════════════════════════════════════════════════════════════
#  LEFT PANEL — EDITOR
# ════════════════════════════════════════════════════════════════════════════

def chain_panel(chain: str):
    """Full editor for one chain (GET or POST)."""
    is_get = chain == "get"
    client_token = "<METADATA>" if is_get else "<OUTPUT>"
    client_section_name = "client.metadata" if is_get else "client.output"

    with ui.column().classes("w-full gap-4 p-2"):

        # ── Body template (client → server) ─────────────────────────
        with ui.row().classes("items-center gap-2"):
            ui.label("Body Template (client → server)").classes(
                "text-sm font-bold text-gray-300"
            )
            _wire_badge("TEXT TEMPLATE", "deep-purple-8")
        body_main = ui.textarea(
            label=f"[raw.{chain}] body",
            value=client_token,
            placeholder=client_token,
        ).classes("w-full font-mono").props('autogrow rows=2')
        body_inputs[(chain, "main")] = body_main

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
                'Each newline in the textarea becomes <code>\\r\\n</code> (CR LF) in the TOML output. '
                'You can also type <code>\\r\\n</code> literally if you prefer single-line entry.'
                '</div>'
            )
            ui.html(
                '<div style="font-size:11px;color:#b0b0b0;margin-top:2px;">'
                '<b>Hex bytes:</b> Use <code>\\xNN</code> for raw byte values in the body '
                '(e.g. <code>\\x00</code> for null). These are preserved as-is in the TOML output.'
                '</div>'
            )

        ui.separator()

        # ── Client transforms & Server response in sub-tabs ─────────
        with ui.tabs().classes("w-full").props("dense active-color=teal") as sub_tabs:
            req_tab = ui.tab("REQ (to server)")
            resp_tab = ui.tab("RESP (from server)")

        with ui.tab_panels(sub_tabs, value=req_tab).classes("w-full"):
            # ── REQ: client transform chain ──────────────────────────
            with ui.tab_panel(req_tab):
                ui.label(f"Transforms for [{client_section_name}]").classes(
                    "text-xs text-gray-500 mb-1"
                )
                transform_chain_editor(chain, "client")

            # ── RESP: server body + server transforms ────────────────
            with ui.tab_panel(resp_tab):
                with ui.row().classes("items-center gap-2"):
                    ui.label("Server Response Body").classes(
                        "text-sm font-bold text-gray-300"
                    )
                    _wire_badge("TEXT TEMPLATE", "deep-purple-8")
                server_default = "<OUTPUT>" if is_get else ""
                server_placeholder = "<OUTPUT>" if is_get else "HTTP/1.1 200 OK\\r\\n\\r\\n"
                body_server = ui.textarea(
                    label=f"[raw.{chain}.server] body",
                    value=server_default,
                    placeholder=server_placeholder,
                ).classes("w-full font-mono").props('autogrow rows=2')
                body_inputs[(chain, "server")] = body_server

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
    """Profile-level options (name, author, protocol)."""
    with ui.column().classes("w-full gap-4 p-4"):
        ui.label("Profile Settings").classes("text-lg font-bold text-gray-200")

        name_input = ui.input(
            label="Profile Name",
            value="My Custom Profile",
            placeholder="e.g. HTTP Mimicry",
        ).classes("w-full")
        option_inputs["name"] = name_input

        author_input = ui.input(
            label="Author",
            placeholder="e.g. operator handle",
        ).classes("w-full")
        option_inputs["author"] = author_input

        proto_toggle = ui.toggle(
            ["tcp", "udp"],
            value="tcp",
        ).classes("w-full")
        option_inputs["proto"] = proto_toggle

        ui.separator()

        with ui.column().classes("gap-2"):
            ui.label("Quick Reference").classes("text-sm font-bold text-gray-400")
            ui.label("TCP — one message per connection (HTTP, FTP, etc.)").classes(
                "text-xs text-gray-500"
            )
            ui.label("UDP — one datagram per transaction (NTP, DNS, SNMP)").classes(
                "text-xs text-gray-500"
            )
            ui.label("~64KB hard limit on UDP datagrams after transform expansion").classes(
                "text-xs text-gray-500"
            )

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

        # ── Text vs Bytes reference ─────────────────────────────────
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
                    ui.label("Transform val / key Fields").classes(
                        "text-xs font-bold text-gray-300"
                    )
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
                    ui.label("Transform Data Flow").classes(
                        "text-xs font-bold text-gray-300"
                    )
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


def left_panel():
    """The full left-side editor panel."""
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

        # Build button pinned at bottom
        ui.button(
            "Build Profile",
            icon="build",
            color="amber-9",
            on_click=do_build,
        ).classes("w-full mt-2").props("unelevated")


# ════════════════════════════════════════════════════════════════════════════
#  RIGHT PANEL — PREVIEW
# ════════════════════════════════════════════════════════════════════════════

@ui.refreshable
def preview_panel():
    """Tabbed preview: Rendered (placeholder) and Raw (codemirror TOML)."""
    with ui.column().classes("w-full h-full"):
        with ui.tabs().classes("w-full").props("dense active-color=cyan") as preview_tabs:
            rendered_tab = ui.tab("Rendered")
            raw_tab = ui.tab("Raw")

        with ui.tab_panels(preview_tabs, value=raw_tab).classes("w-full flex-grow"):
            with ui.tab_panel(rendered_tab):
                with ui.column().classes(
                    "w-full h-full items-center justify-center gap-4"
                ):
                    ui.icon("visibility", size="xl").classes("text-gray-600")
                    ui.label("Rendered preview coming soon").classes(
                        "text-gray-500 text-sm"
                    )

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

    with ui.row().classes("w-full items-center px-4 py-2 gap-2").style(
        "background: #1a1a2e; border-bottom: 1px solid #333;"
    ):
        ui.icon("router", size="sm").classes("text-amber-400")
        ui.label("Profile Builder").classes("text-lg font-bold text-gray-200")
        ui.label("POC v1").classes("text-xs text-gray-500")

    with ui.splitter(value=50).classes("w-full flex-grow").style(
        "height: calc(100vh - 48px);"
    ) as splitter:
        with splitter.before:
            with ui.scroll_area().classes("h-full"):
                left_panel()

        with splitter.after:
            with ui.scroll_area().classes("h-full"):
                preview_panel()


ui.run(port=8090, title="Profile Builder", reload=True)