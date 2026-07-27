import re
import tomllib
from pathlib import Path

import structlog
from nicegui import events, ui

from client.modules.api_calls import (
    get_all_profiles,
    get_profile_by_name,
    preview_profile,
    seed_profiles,
    upload_profile,
)
from client.pages.components.wire_view import render_profile_output
from client.pages.footer import build_footer
from client.pages.formatted_tooltip import formatted_tooltip
from client.pages.menu import setup_menu
from client.utils.helpers import notify

server_log = structlog.getLogger("server")
server_log.info("Loading /profile-preview page")

_LOCAL_PROFILES_DIR = Path(__file__).resolve().parent.parent / "user" / "profiles"


# ════════════════════════════════════════════════════════════════════════════
#  CONSTANTS (module-level, immutable — safe for multi-user)
# ════════════════════════════════════════════════════════════════════════════

TRANSFORMS = {
    "base64": {
        "desc": "Standard Base64 encode/decode",
        "input": False,
        "field": None,
        "wire_in": "raw bytes",
        "wire_out": "ASCII text (A-Za-z0-9+/=)",
    },
    "base64url": {
        "desc": "URL-safe Base64 (no padding)",
        "input": False,
        "field": None,
        "wire_in": "raw bytes",
        "wire_out": "ASCII text (A-Za-z0-9-_)",
    },
    "prepend": {
        "desc": "Prepend literal bytes before data",
        "input": True,
        "field": "val",
        "wire_in": "any",
        "wire_out": "val bytes + original",
        "val_hint": "See 'Input Reference' for additional input info",
        "val_example": "",
    },
    "append": {
        "desc": "Append literal bytes after data",
        "input": True,
        "field": "val",
        "wire_in": "any",
        "wire_out": "original + val bytes",
        "val_hint": "See 'Input Reference' for additional input info",
        "val_example": "",
    },
    "netbios": {
        "desc": "NetBIOS encoding (lowercase a-p)",
        "input": False,
        "field": None,
        "wire_in": "raw bytes",
        "wire_out": "ASCII text (2x size expansion)",
    },
    "netbiosu": {
        "desc": "NetBIOS encoding (uppercase A-P)",
        "input": False,
        "field": None,
        "wire_in": "raw bytes",
        "wire_out": "ASCII text (2x size expansion)",
    },
    "symcrypt": {
        "desc": "AES-256-GCM symmetric encryption",
        "input": True,
        "field": "key",
        "wire_in": "raw bytes",
        "wire_out": "raw bytes (+28B: 12B nonce + 16B tag + ciphertext)",
        "val_hint": "Exactly 32 bytes as \\xNN hex escapes.",
        "val_example": "'\\x6B\\x4A\\x79\\xF6\\xD6\\xDF\\x9B\\xD5...' (32 bytes = 64 hex chars)",
    },
}

TRANSFORM_KEYS = list(TRANSFORMS.keys())


# ════════════════════════════════════════════════════════════════════════════
#  DATA MODEL (pure functions — no mutable module state)
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


# ════════════════════════════════════════════════════════════════════════════
#  TOML PARSING (file → model)
# ════════════════════════════════════════════════════════════════════════════


def _normalize_transform(t: dict) -> dict:
    op = t.get("op", "")
    val = t.get("val", "") or t.get("key", "")
    entry = {"op": op}
    if val:
        entry["val"] = val
    return entry


def parse_toml(toml_str: str) -> dict:
    """Parse a TOML profile string into a profile_model dict."""
    data = tomllib.loads(toml_str)
    model = _empty_model()

    prof = data.get("profile", {})
    model["name"] = prof.get("name", "Untitled Profile")
    model["author"] = prof.get("author", "")

    raw = data.get("raw", {})

    get = raw.get("get", {})
    model["proto"] = get.get("proto", raw.get("post", {}).get("proto", "tcp"))
    model["get"]["body"] = get.get("body", "<METADATA>")

    client_meta = get.get("client", {}).get("metadata", {})
    model["get"]["client_transforms"] = [_normalize_transform(t) for t in client_meta.get("transforms", [])]

    server_get = get.get("server", {})
    model["get"]["server_body"] = server_get.get("body", "<OUTPUT>")

    server_output = server_get.get("output", {})
    model["get"]["server_transforms"] = [_normalize_transform(t) for t in server_output.get("transforms", [])]

    post = raw.get("post", {})
    model["post"]["body"] = post.get("body", "<OUTPUT>")

    client_output = post.get("client", {}).get("output", {})
    model["post"]["client_transforms"] = [_normalize_transform(t) for t in client_output.get("transforms", [])]

    server_post = post.get("server", {})
    model["post"]["server_body"] = server_post.get("body", "")

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

    text = re.sub(r"\\x[0-9A-Fa-f]{2}|\\r|\\n", _protect, text)

    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')

    text = text.replace("\r\n", "\\r\\n")
    text = text.replace("\r", "\\r\\n")
    text = text.replace("\n", "\\r\\n")

    for i, esc in enumerate(escapes):
        text = text.replace(f"{SENTINEL}{i}{SENTINEL}", esc)

    return text


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


def sync_model_from_ui(state):
    """Pull current UI values into the profile model before building TOML."""
    refs = state.ui_refs
    model = state.profile_model

    if "name" in refs:
        model["name"] = refs["name"].value or "Untitled Profile"
    if "author" in refs:
        model["author"] = refs["author"].value or ""
    if "proto" in refs:
        model["proto"] = refs["proto"].value or "tcp"

    for chain in ("get", "post"):
        body_ref = refs.get(f"{chain}_body")
        if body_ref:
            model[chain]["body"] = body_ref.value or ""

        server_body_ref = refs.get(f"{chain}_server_body")
        if server_body_ref:
            model[chain]["server_body"] = server_body_ref.value or ""

        card = refs.get(f"{chain}_client_card")
        if card:
            model[chain]["client_transforms"] = _extract_card_transforms(card)

        if chain == "get":
            server_card = refs.get(f"{chain}_server_card")
            if server_card:
                model[chain]["server_transforms"] = _extract_card_transforms(server_card)


def build_toml(state) -> str:
    """Build TOML from profile_model."""
    m = state.profile_model
    lines = []

    lines.append("[profile]")
    lines.append(f'name = "{_escape_toml_body(m["name"])}"')
    if m["author"]:
        lines.append(f'author = "{_escape_toml_body(m["author"])}"')
    lines.append("")

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


# ════════════════════════════════════════════════════════════════════════════
#  BACKWARD COMPAT — listener.py imports this
# ════════════════════════════════════════════════════════════════════════════


def _render_output(data: dict):
    render_profile_output(data)


# ════════════════════════════════════════════════════════════════════════════
#  PAGE
# ════════════════════════════════════════════════════════════════════════════


@ui.page("/profile-preview")
async def profile_preview_page():
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    setup_menu("Profiles")
    await _profile_editor_view()
    await build_footer()


async def _profile_editor_view():
    # Per-page-instance mutable state
    state = _EditorState()

    profile_names = await _fetch_profile_names()

    # ── Refreshable panels (closures over state) ──────────────────────
    @ui.refreshable
    def editor_panel():
        state.ui_refs.clear()
        with ui.column().classes("w-full h-full gap-0"):
            with ui.tabs().classes("w-full shrink-0").props(
                "dense active-color=emerald indicator-color=emerald text-color=grey-5"
            ) as main_tabs:
                get_tab = ui.tab("GET")
                post_tab = ui.tab("POST")
                opts_tab = ui.tab("OPTIONS")

            with ui.tab_panels(main_tabs, value=get_tab).classes("w-full flex-grow overflow-auto"):
                with ui.tab_panel(get_tab):
                    _chain_panel("get", state)
                with ui.tab_panel(post_tab):
                    _chain_panel("post", state)
                with ui.tab_panel(opts_tab):
                    _options_panel(state)

    @ui.refreshable
    def preview_panel():
        with ui.column().classes("w-full h-full gap-0"):
            with ui.tabs().classes("w-full shrink-0").props(
                "dense active-color=emerald indicator-color=emerald text-color=grey-5"
            ) as preview_tabs:
                raw_toml_tab = ui.tab("PROFILE")
                wire_tab = ui.tab("WIRE VIEW")

            preview_tabs.on_value_change(lambda e: state.__setattr__("_active_preview_tab", e.value))
            initial_tab = getattr(state, "_active_preview_tab", "PROFILE")
            restore_tab = wire_tab if initial_tab == "WIRE VIEW" else raw_toml_tab

            with ui.tab_panels(preview_tabs, value=restore_tab).classes("w-full flex-grow"):
                with ui.tab_panel(raw_toml_tab):
                    ui.codemirror(
                        state.toml_text["value"],
                        language="TOML",
                        theme="androidstudio",
                    ).classes("w-full h-full min-h-[400px]").props("readonly")

                with ui.tab_panel(wire_tab).classes("p-0 h-full"):
                    state.wire_container = ui.column().classes("w-full h-full overflow-hidden")
                    with state.wire_container, ui.column().classes(
                        "w-full h-full items-center justify-center gap-3 opacity-30"
                    ):
                        ui.icon("cable", size="xl", color="neutral-500")
                        ui.label("Click BUILD then RENDER to see wire view").classes("tech-label-sub text-neutral-500")

    # ── Action handlers ───────────────────────────────────────────────
    def do_build():
        sync_model_from_ui(state)
        state.toml_text["value"] = build_toml(state)
        preview_panel.refresh()
        notify("Profile built", type="positive", color="emerald-9")

    async def do_render():
        toml = state.toml_text["value"]

        result = await preview_profile(toml)

        if not result:
            notify("Failed to contact server", type="negative")
            return

        data = result.get("data", {})

        if state.wire_container:
            state.wire_container.clear()
            with state.wire_container:
                render_profile_output(data)

    def do_new():
        state.profile_model = _empty_model()
        state.toml_text["value"] = "# Click BUILD to generate TOML"
        state.current_profile_name = None
        editor_panel.refresh()
        preview_panel.refresh()

    async def on_profile_select(e):
        if not e.value:
            return
        resp = await get_profile_by_name(e.value)
        if resp and resp.get("data", {}).get("artifact_contents"):
            toml_str = resp["data"]["artifact_contents"]
            try:
                state.profile_model = parse_toml(toml_str)
            except Exception as ex:
                notify(f"TOML parse error: {ex}", type="negative")
                return
            state.current_profile_name = e.value
            state.toml_text["value"] = toml_str
            editor_panel.refresh()
            preview_panel.refresh()
            notify(f"Loaded {e.value}", type="positive", color="emerald-9")
        else:
            notify(f"Failed to load {e.value}", type="negative")

    async def refresh_profiles():
        nonlocal profile_names
        profile_names = await _fetch_profile_names()
        state.file_select.options = profile_names
        state.file_select.update()

    async def do_quick_save():
        toml = state.toml_text["value"]
        if not toml or toml.startswith("#"):
            notify("Nothing to save — build first", type="warning", color="orange-9")
            return
        if state.current_profile_name:
            resp = await upload_profile(state.current_profile_name, toml)
            if resp:
                notify(f"Saved {state.current_profile_name}", type="positive", color="emerald-9")
            else:
                notify("Save failed", type="negative")
        else:
            await do_save_as()

    async def do_save_as():
        toml = state.toml_text["value"]
        if not toml or toml.startswith("#"):
            notify("Nothing to save — build first", type="warning", color="orange-9")
            return
        default_name = state.current_profile_name or "profile.toml"

        with ui.dialog() as d, ui.card().classes("tech-dialog w-96 p-0 rounded overflow-hidden"):
            with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
                ui.label("SAVE_AS").classes("tech-label-sub")
                ui.button(icon="close", on_click=d.close).props("dense flat size=sm color=grey")

            with ui.column().classes("p-4 gap-4 w-full"):
                name_input = (
                    ui.input("FILENAME", value=default_name)
                    .props("outlined dense dark color=emerald")
                    .classes("w-full tech-input")
                )

            with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"):
                ui.button("CANCEL", on_click=d.close).props("flat dense color=grey no-caps")

                async def finalize():
                    filename = (name_input.value or "").strip()
                    if not filename:
                        notify("Enter a filename", type="warning", color="orange-9")
                        return
                    if not filename.endswith(".toml"):
                        filename += ".toml"
                    resp = await upload_profile(filename, state.toml_text["value"])
                    if not resp:
                        notify("Save failed", type="negative")
                        return
                    state.current_profile_name = filename
                    d.close()
                    await refresh_profiles()
                    state.file_select.set_value(filename)
                    notify(f"Saved {filename}", type="positive", color="emerald-9")

                ui.button("SAVE", on_click=finalize).props("unelevated dense color=emerald no-caps")

        d.open()

    # ── Load dialog ───────────────────────────────────────────────────
    def show_load_dialog():
        with ui.dialog().props("maximized=false") as dialog, ui.card().classes(
            "tech-dialog w-[600px] max-h-[80vh] p-0 rounded overflow-hidden flex flex-col"
        ):
            with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
                with ui.row().classes("gap-2 items-center"):
                    ui.icon("folder_open", color="emerald-500")
                    ui.label("LOAD PROFILE").classes("tech-label-sub")
                ui.button(icon="close", on_click=dialog.close).props("dense flat size=sm color=grey")

            with ui.column().classes("p-5 gap-4 w-full flex-grow overflow-auto"):
                ui.label("Upload a .toml file:").classes("tech-label-sub text-neutral-400")

                async def _on_upload(e: events.UploadEventArguments):
                    try:
                        content = (await e.file.read()).decode("utf-8")
                    except Exception as ex:
                        notify(f"File read error: {ex}", type="negative")
                        return
                    try:
                        state.profile_model = parse_toml(content)
                    except Exception as ex:
                        notify(f"TOML parse error: {ex}", type="negative")
                        return
                    state.toml_text["value"] = content
                    state.current_profile_name = None
                    editor_panel.refresh()
                    preview_panel.refresh()
                    dialog.close()
                    notify(f"Loaded: {state.profile_model['name']}", type="positive", color="emerald-9")

                ui.upload(
                    label="SELECT .TOML PROFILE",
                    auto_upload=True,
                    on_upload=_on_upload,
                ).props("flat bordered dark color=emerald accept=.toml").classes("w-full bg-black/20")

                ui.separator().classes("bg-white/5")

                ui.label("Or paste TOML directly:").classes("tech-label-sub text-neutral-400")
                paste_area = (
                    ui.textarea(placeholder="Paste TOML here...")
                    .props('outlined dark color=emerald input-class="font-mono text-[11px]" rows=6')
                    .classes("w-full tech-input")
                )

            with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3 shrink-0"):
                ui.button("CANCEL", on_click=dialog.close).props("flat dense color=grey no-caps")

                def _load_pasted():
                    if not paste_area.value or not paste_area.value.strip():
                        return
                    try:
                        state.profile_model = parse_toml(paste_area.value)
                    except Exception as ex:
                        notify(f"TOML parse error: {ex}", type="negative")
                        return
                    state.toml_text["value"] = paste_area.value
                    state.current_profile_name = None
                    editor_panel.refresh()
                    preview_panel.refresh()
                    dialog.close()
                    notify(f"Loaded: {state.profile_model['name']}", type="positive", color="emerald-9")

                ui.button("LOAD", on_click=_load_pasted).props(
                    "unelevated dense color=emerald text-color=white no-caps"
                )

        dialog.open()

    # ── Seed defaults ─────────────────────────────────────────────────
    async def do_seed_defaults():
        if not _LOCAL_PROFILES_DIR.is_dir():
            notify("No local profile directory found", type="warning", color="orange-9")
            return
        profiles = []
        for p in sorted(_LOCAL_PROFILES_DIR.glob("*.toml")):
            try:
                profiles.append({"profile_name": p.name, "profile_contents": p.read_text()})
            except Exception:
                continue
        if not profiles:
            notify("No local .toml files found to seed", type="warning", color="orange-9")
            return
        resp = await seed_profiles(profiles)
        if resp and resp.get("data"):
            d = resp["data"]
            notify(
                f"Seeded: {d.get('created', 0)} new, {d.get('updated', 0)} updated, "
                f"{d.get('unchanged', 0)} unchanged",
                type="positive",
                color="emerald-9",
            )
            await refresh_profiles()
        else:
            notify("Seed failed — check server connection", type="negative")

    # ── Upload profile file ───────────────────────────────────────────
    def upload_profile_file():
        upload_state = {"filename": "", "contents": ""}

        async def handle_upload(e):
            try:
                file_bytes = await e.file.read()
                upload_state["filename"] = e.file.name
                upload_state["contents"] = file_bytes.decode("utf-8")
                submit_btn.enable()
            except Exception as err:
                notify(f"Failed to read file: {err}", type="negative")

        async def submit():
            if not upload_state["contents"]:
                return
            name = upload_state["filename"]
            if not name.endswith(".toml"):
                name += ".toml"
            submit_btn.props("loading")
            resp = await upload_profile(name, upload_state["contents"])
            submit_btn.props(remove="loading")
            if resp:
                notify(f"Uploaded {name}", type="positive", color="emerald-9")
                dlg.close()
                await refresh_profiles()
                state.file_select.set_value(name)
            else:
                notify("Upload failed", type="negative")

        with ui.dialog() as dlg, ui.card().classes("tech-dialog w-[500px] p-0 rounded overflow-hidden"):
            with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
                with ui.row().classes("gap-2 items-center"):
                    ui.icon("upload_file", color="emerald-500")
                    ui.label("UPLOAD PROFILE").classes("tech-label-sub")
                ui.button(icon="close", on_click=dlg.close).props("dense flat size=sm color=grey")

            with ui.column().classes("p-5 gap-4 w-full"):
                ui.upload(
                    label="SELECT .TOML PROFILE",
                    auto_upload=True,
                    max_files=1,
                    on_upload=handle_upload,
                ).props("flat bordered dark color=emerald accept=.toml").classes("w-full bg-black/20")

            with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"):
                ui.button("CANCEL", on_click=dlg.close).props("flat dense color=grey no-caps")
                submit_btn = (
                    ui.button("UPLOAD", on_click=submit)
                    .props("unelevated dense color=emerald text-color=white no-caps")
                    .classes("font-bold tracking-wide")
                )
                submit_btn.disable()

        dlg.open()

    # ══════════════════════════════════════════════════════════════════
    #  MAIN LAYOUT
    # ══════════════════════════════════════════════════════════════════

    with ui.element().classes("w-full h-full gap-0"):  # noqa: SIM117
        with ui.splitter(value=42, limits=(25, 65)).classes("w-full h-full").props(
            "separator-class=bg-white/10 separator-style=width:1px"
        ) as splitter:
            with splitter.before:  # noqa: SIM117
                with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
                    # Header bar
                    with ui.row().classes(  # noqa: SIM117
                        "w-full items-center justify-between tech-header-bar px-4 shrink-0"
                    ):
                        with ui.row().classes("items-center gap-3"):
                            ui.icon("router", color="emerald-500").classes("text-xl")
                            ui.label("PROFILE_BUILDER //").classes("tech-label-header-section")

                    # Profile selector row
                    with ui.row().classes("w-full items-center gap-2 px-3 pt-3 pb-1 shrink-0"):
                        state.file_select = (
                            ui.select(
                                options=profile_names,
                                label="Load Existing Profile",
                                value=None,
                                on_change=on_profile_select,
                            )
                            .props("outlined dense dark color=emerald options-dense clearable")
                            .classes("flex-grow tech-select")
                        )
                        with (
                            ui.button(icon="upload_file", on_click=show_load_dialog)
                            .props("flat dense size=xs")
                            .classes("tech-btn-action-2")
                        ):
                            formatted_tooltip("Upload Profile to Server")
                        with (
                            ui.button(icon="refresh", on_click=refresh_profiles)
                            .props("flat dense size=xs")
                            .classes("tech-btn-secondary")
                        ):
                            formatted_tooltip("Refresh List")

                    # Seed banner
                    if not profile_names:
                        with ui.row().classes(
                            "w-full items-center gap-2 px-3 py-2 bg-amber-500/10 " "border-b border-amber-500/20"
                        ):
                            ui.icon("info", size="xs", color="amber-400")
                            ui.label("No profiles on server.").classes("tech-label-sub text-amber-400 text-xs")
                            ui.button(
                                "SEED DEFAULTS",
                                on_click=do_seed_defaults,
                            ).props("flat dense size=xs color=amber no-caps")

                    # Editor body (scrollable)
                    with ui.scroll_area().classes("w-full flex-grow"):
                        editor_panel()

                    # Bottom action bar
                    with ui.row().classes(
                        "w-full items-center justify-between px-3 py-2 border-t "
                        "border-white/5 bg-black/20 shrink-0 gap-2"
                    ):
                        with ui.row().classes("items-center gap-1"):
                            with (
                                ui.button(icon="note_add", on_click=do_new)
                                .props("flat dense size=sm")
                                .classes("tech-btn-secondary")
                            ):
                                formatted_tooltip("New Profile")
                            with (
                                ui.button(icon="save", on_click=do_quick_save)
                                .props("flat dense size=sm")
                                .classes("tech-btn-secondary")
                            ):
                                formatted_tooltip("Save")
                            with (
                                ui.button(icon="save_as", on_click=do_save_as)
                                .props("flat dense size=sm")
                                .classes("tech-btn-secondary")
                            ):
                                formatted_tooltip("Save As")

                        with ui.row().classes("items-center gap-1"):
                            ui.button(
                                "BUILD",
                                icon="build",
                                on_click=lambda: _render_and_build(),
                            ).props("unelevated dense no-caps size=sm").classes(
                                "bg-emerald-600 text-white font-bold tracking-wide text-xs px-4"
                            )

                            # quick helper to run do_build and do_render in one shot
                            async def _render_and_build():
                                do_build()
                                await do_render()

            with splitter.after:  # noqa: SIM117
                with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
                    with ui.row().classes("w-full items-center gap-3 tech-header-bar px-4 shrink-0"):
                        ui.icon("analytics", color="emerald-500").classes("text-xl")
                        ui.label("PROFILE_OUTPUT //").classes("tech-label-header-section")

                    preview_panel()


# ════════════════════════════════════════════════════════════════════════════
#  EDITOR COMPONENTS (used inside editor_panel)
# ════════════════════════════════════════════════════════════════════════════


class _EditorState:
    """Per-page-instance mutable state for the profile editor."""

    def __init__(self):
        self.profile_model: dict = _empty_model()
        self.ui_refs: dict = {}
        self.toml_text: dict = {"value": "# Click BUILD to generate TOML"}
        self.current_profile_name: str | None = None
        self.file_select: ui.select | None = None
        self.wire_container = None


def _wire_badge(label: str, color: str = "grey-8") -> ui.badge:
    return ui.badge(label, color=color).props("outline dense").classes("text-[10px]")


def _render_wire_flow(container, info: dict):
    container.clear()
    with container, ui.row().classes("items-center gap-1"):
        ui.label("Wire:").classes("text-[10px] text-gray-600")
        _wire_badge(info.get("wire_in", "any"), "blue-grey-7")
        ui.icon("arrow_forward", size="xs").classes("text-gray-600")
        _wire_badge(info.get("wire_out", "any"), "teal-8")


def _body_hint_block():
    with ui.column().classes("gap-0 -mt-2").style("border-left: 2px solid #5c4d8a; padding-left: 8px;"):
        ui.html(
            '<div style="font-size:11px;color:#9e9e9e;line-height:1.6;">'
            "The <b>body</b> field is the <code>container</code> the data we are smuggling "
            "is wrapped in. Based on which communication step the implant is on, different "
            "types of data will be contained in it. These are represented by <b>tokens</b>:"
            '<ul style="margin:4px 0 4px 16px;padding:0;">'
            '<li><code style="color:#80cbc4;">&lt;METADATA&gt;</code> '
            "(GET REQ &rarr; Server)</li>"
            '<li><code style="color:#80cbc4;">&lt;OUTPUT&gt;</code> '
            "(POST REQ -> implant, GET &amp; POST RESP &rarr; Implant)</li>"
            "</ul>"
            "Tokens are the only fields replaced with the <em>transformed</em> payload data. "
            "Everything else in the profile is <b>literal Text (ASCII)</b>, or <b>bytes</b> on the wire (see below)."
            "</div>"
        )


def _general_hint_block():
    ui.label("Text, Bytes, and Newlines:").classes("tech-label")
    ui.html(
        '<div style="font-size:11px;color:#b0b0b0;margin-top:2px;">'
        "<b>Text (ASCII):</b> Any text entered, no escpaes. i.e.: <code>abcd1234</code>"
        "</div>"
    )
    ui.html(
        '<div style="font-size:11px;color:#ffcc80;margin-top:2px;">'
        "<b>Newlines:</b> You can type/paste multi-line text into the <b>BODY</b> field (e.g. HTTP headers). "
        "Each newline becomes <code>\\r\\n</code> (CR LF) in the TOML output. "
        "You can also type <code>\\r\\n</code> literally if you prefer single-line entry. "
        "Transforms <b><i>do not</i></b> support multiline copy/paste, only Text or Bytes.<br>"
        'For example, to do a HTTP newline in the "append" transform, type <code>\\r\\n</code>'
        "</div>"
    )
    ui.html(
        '<div style="font-size:11px;color:#b0b0b0;margin-top:2px;">'
        "<b>Hex bytes:</b> Use <code>\\xNN</code> for raw byte values "
        "(e.g. <code>\\x00</code> for null). These are preserved as-is in the TOML output."
        "</div>"
    )

    ui.label("Examples:")
    ui.code("Text: 'GET /'").classes("dense w-full")
    ui.code(r"Binary: '\x23\x00\x06\xEC'").classes("dense w-full")
    ui.code(r"Mixed: 'GET /sid=\x0D\x0A'").classes("dense w-full")


def _add_transform(card, op: str = "base64", val: str = ""):
    """Add a draggable transform entry to a card."""
    info = TRANSFORMS.get(op, TRANSFORMS["base64"])
    needs_input = info.get("input", False)

    with card, ui.expansion(text=op).classes("w-full tech-expansion") as expansion:
        with expansion.add_slot("header"), ui.row().classes("items-center gap-2 w-full"):
            ui.icon("drag_indicator").classes("drag-handle cursor-grab active:cursor-grabbing text-gray-400")
            expansion_label = ui.label(op).style("font-weight: 500")

        expansion.transform_op = (
            ui.select(
                TRANSFORM_KEYS,
                value=op,
                label="Operation",
                on_change=lambda: _on_transform_change(
                    expansion,
                    expansion_label,
                    wire_flow_container,
                    val_hint_label,
                    val_example_label,
                ),
            )
            .props("outlined dense dark color=emerald options-dense")
            .classes("w-full tech-select")
        )

        expansion.transform_desc = ui.label(info.get("desc", "")).classes("text-xs text-gray-500")

        wire_flow_container = ui.column().classes("w-full gap-0")
        _render_wire_flow(wire_flow_container, info)

        field = info.get("field", "val")
        if field == "key":
            lbl = "Key — raw bytes as \\xNN hex escapes"
            ph = "\\x6B\\x4A\\x79\\xF6..."
        else:
            lbl = "Value — text or \\xNN hex bytes"
            ph = "\\x0D\\x0A or plain text"

        expansion.transform_val = (
            ui.input(label=lbl, value=val, placeholder=ph)
            .props("outlined dense dark color=emerald")
            .classes("w-full font-mono tech-input")
        )
        expansion.transform_val.set_visibility(needs_input)

        val_hint_label = ui.label(info.get("val_hint", "")).classes("text-[11px] text-amber-400")
        val_hint_label.set_visibility(needs_input)
        val_example_label = ui.label(info.get("val_example", "")).classes("text-[10px] text-gray-500 font-mono")
        val_example_label.set_visibility(needs_input)

        ui.button(
            "Delete",
            icon="delete",
            color="red-9",
            on_click=lambda _e=None, exp=expansion: exp.delete(),
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
            'label="Key — raw bytes as \\\\xNN hex escapes"' ' placeholder="\\x6B\\x4A\\x79\\xF6..."'
        )
    else:
        expansion.transform_val.props(
            'label="Value — text or \\\\xNN hex bytes"' ' placeholder="\\x0D\\x0A or plain text"'
        )

    expansion.transform_desc.set_text(info.get("desc", ""))
    val_hint_label.set_text(info.get("val_hint", ""))
    val_example_label.set_text(info.get("val_example", ""))

    _render_wire_flow(wire_flow_container, info)


def _transform_chain_editor(chain: str, sub_chain: str, state):
    """Render a transform chain editor, pre-populated from the model."""
    with ui.column().classes("w-full gap-2"):
        card = (
            ui.card()
            .classes("w-full min-h-[60px]")
            .style("border: 1px dashed #444; background: transparent; padding: 8px;")
        )

        state.ui_refs[f"{chain}_{sub_chain}_card"] = card

        if sub_chain == "client":
            transforms = state.profile_model[chain].get("client_transforms", [])
        else:
            transforms = state.profile_model[chain].get("server_transforms", [])

        for t in transforms:
            _add_transform(card, op=t["op"], val=t.get("val", ""))

        card.make_sortable(handle=".drag-handle")

        ui.button(
            "Add Transform",
            icon="add",
            on_click=lambda _e=None, c=card: _add_transform(c),
        ).props("outline dense").classes("w-full tech-btn-action-2")


def _chain_panel(chain: str, state):
    """Editor for one chain (get or post)."""
    m = state.profile_model[chain]
    is_get = chain == "get"
    client_token = "<METADATA>" if is_get else "<OUTPUT>"
    client_section_name = "client.metadata" if is_get else "client.output"

    with ui.column().classes("w-full gap-4 p-3"):
        with ui.expansion("Input Reference", value=True).classes("w-full tech-expansion"):
            _body_hint_block()
            _general_hint_block()

        with ui.tabs().classes("w-full").props(
            "dense active-color=teal indicator-color=teal text-color=grey-5"
        ) as sub_tabs:
            req_tab = ui.tab("REQ (to server)")
            resp_tab = ui.tab("RESP (from server)")

        with ui.tab_panels(sub_tabs, value=req_tab).classes("w-full"):
            with ui.tab_panel(req_tab):
                with ui.row().classes("items-center gap-2"):
                    ui.label("Body Template (client → server)").classes("text-sm font-bold text-gray-300")

                body_input = (
                    ui.textarea(
                        label=f"[raw.{chain}] body",
                        value=m["body"],
                        placeholder=client_token,
                    )
                    .props('outlined dark color=emerald input-class="font-mono text-[11px]" autogrow rows=2')
                    .classes("w-full tech-input")
                )
                state.ui_refs[f"{chain}_body"] = body_input

                ui.separator().classes("bg-white/5")

                ui.label(f"Transforms for [{client_section_name}]").classes("text-xs text-gray-500 mb-1")
                _transform_chain_editor(chain, "client", state)

            with ui.tab_panel(resp_tab):
                with ui.row().classes("items-center gap-2"):
                    ui.label("Server Response Body").classes("text-sm font-bold text-gray-300")
                    # _wire_badge("TEXT TEMPLATE", "deep-purple-8")

                server_default = m.get("server_body", "<OUTPUT>" if is_get else "")
                server_ph = "<OUTPUT>" if is_get else "HTTP/1.1 200 OK\\r\\n\\r\\n"

                server_body_input = (
                    ui.textarea(
                        label=f"[raw.{chain}.server] body",
                        value=server_default,
                        placeholder=server_ph,
                    )
                    .props('outlined dark color=emerald input-class="font-mono text-[11px]" autogrow rows=2')
                    .classes("w-full tech-input")
                )
                state.ui_refs[f"{chain}_server_body"] = server_body_input

                if is_get:
                    ui.label(
                        "Server response template. <OUTPUT> is replaced with transformed "
                        "task data. Surrounding text is sent as literal bytes."
                    ).classes("text-[11px] text-gray-500 -mt-2")
                    ui.separator().classes("bg-white/5 my-2")
                    ui.label("Transforms for [server.output]").classes("text-xs text-gray-500 mb-1")
                    _transform_chain_editor(chain, "server", state)
                else:
                    with ui.column().classes("gap-1 mt-1").style("border-left: 2px solid #5c4d8a; padding-left: 8px;"):
                        ui.label(
                            "POST server body is the ACK sent back to the implant. There is no beacon data being sent "
                            "between the Implant and Server, and as such, no transforms are needed. "
                        ).classes("text-[11px] text-gray-500")
                        # ui.label(
                        #     "Leave empty for fire-and-forget (e.g. NTP, DNS). "
                        #     "Set to 'HTTP/1.1 200 OK\\r\\n\\r\\n' for HTTP ACK."
                        # ).classes("text-[11px] text-gray-500")


def _options_panel(state):
    """Profile settings and reference documentation panel."""
    m = state.profile_model

    with ui.column().classes("w-full gap-4 p-3"):
        ui.label("Profile Settings").classes("text-sm font-bold text-gray-200")

        name_input = (
            ui.input(label="Profile Name", value=m["name"], placeholder="e.g. HTTP Mimicry")
            .props("outlined dense dark color=emerald")
            .classes("w-full tech-input")
        )
        state.ui_refs["name"] = name_input

        author_input = (
            ui.input(label="Author", value=m["author"], placeholder="e.g. operator handle")
            .props("outlined dense dark color=emerald")
            .classes("w-full tech-input")
        )
        state.ui_refs["author"] = author_input

        ui.separator().classes("bg-white/5")

        ui.label("Profile Protocol")
        proto_toggle = ui.toggle(["tcp", "udp"], value=m["proto"]).classes("w-full tech-toggle")
        state.ui_refs["proto"] = proto_toggle

        ui.separator().classes("bg-white/5")

        with ui.column().classes("gap-2"):
            ui.label("Quick Reference").classes("text-sm font-bold text-gray-400")
            ui.label("TCP — one message per connection (HTTP, FTP, etc.)").classes("text-xs text-gray-500")
            ui.label("UDP — one datagram per transaction (NTP, DNS, SNMP)").classes("text-xs text-gray-500")
            ui.label("~64KB hard limit on UDP datagrams after transform expansion").classes("text-xs text-gray-500")

        ui.separator().classes("bg-white/5")

        ui.label("Available Tokens").classes("text-sm font-bold text-gray-400")
        for token, desc in [
            ("<METADATA>", "Encoded beacon metadata (GET body)"),
            ("<OUTPUT>", "Encoded exfil data / tasks (POST body, server responses)"),
        ]:
            with ui.row().classes("items-center gap-2"):
                ui.badge(token, color="teal-9").props("outline")
                ui.label(desc).classes("text-xs text-gray-500")

        ui.separator().classes("bg-white/5")

        ui.label("Additional info").classes("text-sm font-bold text-gray-400")
        with ui.column().classes("gap-3 w-full"):  # noqa - nicegui, also allows for more cards in a column later
            with ui.card().classes("w-full").style("background: #1e2a3a; border: 1px solid #2a4060; padding: 12px;"):
                with ui.row().classes("items-center gap-2 mb-1"):
                    ui.icon("swap_horiz", size="xs").classes("text-amber-400")
                    ui.label("Transform Data Flow").classes("text-xs font-bold text-gray-300")
                ui.html(
                    '<div style="font-size:11px;color:#b0b0b0;line-height:1.6;">'
                    '1. Raw payload starts as <b style="color:#90caf9;">binary msgpack bytes</b><br>'
                    "2. Each transform runs <b>in order, top to bottom</b><br>"
                    "3. Output of one transform feeds into the next<br>"
                    "4. Final result replaces the token in the body template<br>"
                    '5. Body template + replaced token = <b style="color:#a5d6a7;">bytes on the wire</b>'
                    "</div>"
                )


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════


async def _fetch_profile_names() -> list[str]:
    try:
        resp = await get_all_profiles()
        if resp and resp.get("data"):
            return sorted([p["artifact_name"] for p in resp["data"]], key=str.lower)
    except Exception:
        pass
    return []
