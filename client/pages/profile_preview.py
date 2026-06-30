from pathlib import Path

import structlog
from nicegui import ui

from client.modules.api_calls import (
    get_all_profiles,
    get_profile_by_name,
    preview_profile,
    seed_profiles,
    upload_profile,
)
from client.pages.footer import build_footer
from client.pages.menu import setup_menu
from client.utils.helpers import notify

server_log = structlog.getLogger("server")
server_log.info("Loading /profile-preview page")

_LOCAL_PROFILES_DIR = Path(__file__).resolve().parent.parent / "user" / "profiles"


@ui.page("/profile-preview")
async def profile_preview_page():
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    setup_menu("Profile Preview")
    await profile_preview_view()
    await build_footer()


async def profile_preview_view():
    with ui.element().classes("w-full h-full gap-0"):  # noqa: SIM117
        with ui.splitter(value=38, limits=(20, 65)).classes("w-full h-full").props(
            "separator-class=bg-white/10 separator-style=width:1px"
        ) as splitter:
            with splitter.before:
                await _input_panel()
            with splitter.after:
                await _output_panel()


# ---------------------------------------------------------------------------
# Input panel — file selector + textarea + render button
# ---------------------------------------------------------------------------

_output_container: ui.column | None = None
_textarea: ui.textarea | None = None
_current_profile_name: str | None = None
_file_select: ui.select | None = None


async def _fetch_profile_names() -> list[str]:
    try:
        resp = await get_all_profiles()
        if resp and resp.get("data"):
            return sorted([p["artifact_name"] for p in resp["data"]], key=str.lower)
    except Exception:
        pass
    return []


async def _input_panel():
    global _textarea, _file_select

    profile_names = await _fetch_profile_names()

    async def on_file_select(e):
        global _current_profile_name
        if not e.value or _textarea is None:
            return
        resp = await get_profile_by_name(e.value)
        if resp and resp.get("data", {}).get("artifact_contents"):
            _current_profile_name = e.value
            _textarea.value = resp["data"]["artifact_contents"]
            notify(f"Loaded {e.value}", type="positive", color="emerald-9")
        else:
            notify(f"Failed to load {e.value}", type="negative")

    async def refresh_files():
        nonlocal profile_names
        profile_names = await _fetch_profile_names()
        file_select.options = profile_names
        file_select.update()

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        with ui.row().classes("w-full items-center justify-between tech-header-bar px-4 shrink-0"):  # noqa: SIM117
            with ui.row().classes("items-center gap-3"):
                ui.icon("tune", color="emerald-500").classes("text-xl")
                ui.label("PROFILE_INPUT //").classes("tech-label-header-section")

        # File selector row — above the textarea
        with ui.row().classes("w-full items-center gap-2 px-3 pt-3 pb-1 shrink-0"):
            file_select = (
                ui.select(
                    options=profile_names,
                    label="Load Existing Profile",
                    value=None,
                    on_change=on_file_select,
                )
                .props("outlined dense dark color=emerald options-dense clearable")
                .classes("flex-grow tech-select")
            )
            _file_select = file_select
            ui.button(icon="upload_file", on_click=lambda: _upload_profile_file(file_select)).props(
                "flat dense size=xs color=emerald"
            ).tooltip("Upload Profile")
            ui.button(icon="refresh", on_click=refresh_files).props("flat dense size=xs color=grey")

        # Seed banner — shown when server has no profiles
        if not profile_names:
            with ui.row().classes("w-full items-center gap-2 px-3 py-2 bg-amber-500/10 border-b border-amber-500/20"):
                ui.icon("info", size="xs", color="amber-400")
                ui.label("No profiles on server.").classes("tech-label-sub text-amber-400 text-xs")
                ui.button(
                    "SEED DEFAULTS",
                    on_click=lambda: _do_seed_defaults(file_select),
                ).props("flat dense size=xs color=amber no-caps")

        with ui.column().classes("flex-grow overflow-hidden px-3 pb-3 pt-2 w-full gap-0"):
            _textarea = (
                ui.textarea(placeholder="Paste TOML profile here, or select one above...")
                .props('outlined dark color=emerald input-class="font-mono text-[11px]"')
                .classes("w-full h-full tech-input tech-input-grow")
            )

        with ui.row().classes(  # noqa: SIM117
            "w-full items-center justify-between px-3 py-2 border-t border-white/5 bg-black/20 shrink-0 gap-2"
        ):
            ui.label("Sample payload: PREVIEW_PAYLOAD").classes("tech-label-sub text-neutral-600 text-[10px]")

            with ui.row().classes("items-center gap-1"):
                ui.button(icon="save", on_click=_do_quick_save).props("flat dense size=sm color=grey").tooltip("Save")
                ui.button(icon="save_as", on_click=_do_save_as).props("flat dense size=sm color=grey").tooltip(
                    "Save As"
                )
                render_btn = (
                    ui.button("RENDER", icon="play_arrow", on_click=lambda: _do_render(render_btn))
                    .props("unelevated dense no-caps")
                    .classes("bg-emerald-600 text-white font-bold tracking-wide text-xs px-4 ml-1")
                )


# ---------------------------------------------------------------------------
# Seed defaults
# ---------------------------------------------------------------------------


async def _do_seed_defaults(file_select_widget):
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
            f"Seeded: {d.get('created', 0)} new, {d.get('updated', 0)} updated, {d.get('unchanged', 0)} unchanged",
            type="positive",
            color="emerald-9",
        )
        new_names = await _fetch_profile_names()
        file_select_widget.options = new_names
        file_select_widget.update()
    else:
        notify("Seed failed — check server connection", type="negative")


# ---------------------------------------------------------------------------
# Upload profile file
# ---------------------------------------------------------------------------


def _upload_profile_file(file_select_widget):
    """Open a dialog to upload a .toml profile file to the server."""
    state = {"filename": "", "contents": ""}

    async def handle_upload(e):
        try:
            file_bytes = await e.file.read()
            state["filename"] = e.file.name
            state["contents"] = file_bytes.decode("utf-8")
            submit_btn.enable()
        except Exception as err:
            notify(f"Failed to read file: {err}", type="negative")

    async def submit():
        if not state["contents"]:
            return
        name = state["filename"]
        if not name.endswith(".toml"):
            name += ".toml"

        submit_btn.props("loading")
        resp = await upload_profile(name, state["contents"])
        submit_btn.props(remove="loading")

        if resp:
            notify(f"Uploaded {name}", type="positive", color="emerald-9")
            dlg.close()
            new_names = await _fetch_profile_names()
            file_select_widget.options = new_names
            file_select_widget.set_value(name)
            file_select_widget.update()
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


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------


async def _do_quick_save():
    if _textarea is None or not (_textarea.value or "").strip():
        notify("Nothing to save", type="warning", color="orange-9")
        return
    if _current_profile_name:
        resp = await upload_profile(_current_profile_name, _textarea.value)
        if resp:
            notify(f"Saved {_current_profile_name}", type="positive", color="emerald-9")
        else:
            notify("Save failed", type="negative")
    else:
        await _do_save_as()


async def _do_save_as():
    if _textarea is None or not (_textarea.value or "").strip():
        notify("Nothing to save", type="warning", color="orange-9")
        return
    default_name = _current_profile_name or "profile.toml"

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
            ui.button("SAVE", on_click=lambda: _finalize_save_as(d, name_input)).props(
                "unelevated dense color=emerald no-caps"
            )

    d.open()


async def _finalize_save_as(dialog, name_input):
    global _current_profile_name, _file_select

    filename = (name_input.value or "").strip()
    if not filename:
        notify("Enter a filename", type="warning", color="orange-9")
        return
    if not filename.endswith(".toml"):
        filename += ".toml"

    resp = await upload_profile(filename, _textarea.value)
    if not resp:
        notify("Save failed", type="negative")
        return

    _current_profile_name = filename
    dialog.close()

    if _file_select is not None:
        new_names = await _fetch_profile_names()
        _file_select.options = new_names
        _file_select.set_value(filename)
        _file_select.update()

    notify(f"Saved {filename}", type="positive", color="emerald-9")


# ---------------------------------------------------------------------------
# Right panel — rendered output
# ---------------------------------------------------------------------------


async def _output_panel():
    global _output_container

    with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
        # Header
        with ui.row().classes("w-full items-center gap-3 tech-header-bar px-4 shrink-0"):
            ui.icon("analytics", color="emerald-500").classes("text-xl")
            ui.label("RENDERED_PROFILE //").classes("tech-label-header-section")

        # Placeholder shown before first render
        _output_container = ui.column().classes("w-full flex-grow overflow-hidden")
        with _output_container:
            _render_placeholder()


def _render_placeholder():
    with ui.column().classes("w-full h-full items-center justify-center gap-3 opacity-30"):
        ui.icon("analytics", size="xl", color="emerald-500")
        ui.label("Paste or select a profile and click RENDER").classes("tech-label-sub text-neutral-500")


# ---------------------------------------------------------------------------
# Render handler
# ---------------------------------------------------------------------------


async def _do_render(render_btn):
    global _output_container

    toml_text = (_textarea.value or "").strip() if _textarea else ""
    if not toml_text:
        notify("Paste a TOML profile first", type="warning", color="orange-9")
        return

    render_btn.props("loading")
    try:
        result = await preview_profile(toml_text)
    finally:
        render_btn.props("loading=false")

    if not result:
        notify("Failed to contact server", type="negative")
        return

    data = result.get("data", {})

    _output_container.clear()
    with _output_container:
        _render_output(data)


# ---------------------------------------------------------------------------
# Output rendering helpers
# ---------------------------------------------------------------------------


def _render_output(data: dict):
    protocol_sections = []
    for i, entry in enumerate(data.get("raw_profiles", [])):
        name = entry.get("name", f"raw_{i}")
        tab_label = f"RAW_{name.upper()}" if name != "default" else "RAW"
        protocol_sections.append((tab_label, entry, _render_raw_entry))
    if data.get("smb"):
        protocol_sections.append(("SMB", data["smb"], _render_smb_section))

    tab_names = [s[0] for s in protocol_sections] + ["VALIDATION"]
    default_tab = tab_names[0]

    # Profile metadata bar
    profile_name = data.get("profile_name", "")
    profile_author = data.get("profile_author", "")
    if profile_name or profile_author:
        with ui.row().classes("items-center gap-3 px-4 py-2 border-b border-white/5 bg-black/20 w-full shrink-0"):
            ui.label(profile_name or "Unnamed Profile").classes("tech-label-sub text-emerald-400 font-bold")
            if profile_author:
                ui.label(f"by {profile_author}").classes("tech-label-sub text-neutral-500")

    # Tab strip
    with ui.row().classes("w-full border-b border-white/5 bg-black/40 px-2 shrink-0"):
        tabs = ui.tabs().props("dense indicator-color=emerald text-color=grey-5")
        with tabs:
            for tab_name in tab_names:
                ui.tab(tab_name, label=tab_name).classes("h-10 min-h-0 tech-label-sub")

    # Tab panels
    with ui.tab_panels(tabs, value=default_tab).classes("w-full flex-grow"):
        for tab_name, section_data, render_fn in protocol_sections:
            with ui.tab_panel(tab_name).classes("p-0"):  # noqa: SIM117
                with ui.scroll_area().classes("w-full h-full"):
                    with ui.column().classes("w-full p-5 gap-5"):
                        render_fn(section_data)

        with ui.tab_panel("VALIDATION").classes("p-0"):  # noqa: SIM117
            with ui.scroll_area().classes("w-full h-full"):
                with ui.column().classes("w-full p-5 gap-3"):
                    _render_validation(data.get("validation", {}))


def _render_raw_side(label: str, side: dict | None):
    if not side:
        ui.label(f"No {label} configured").classes("tech-label-sub text-neutral-500 italic")
        return

    ui.label(label).classes("tech-label-header-section")

    with ui.row().classes("items-center gap-2"):
        ui.label("PROTO").classes("tech-label-sub text-neutral-500 w-24 shrink-0")
        ui.label(side.get("proto", "tcp").upper()).classes(
            "text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded"  # noqa
        )

    client = side.get("client", {})
    server = side.get("server", {})

    if client.get("body"):
        with ui.row().classes("items-center gap-2"):
            ui.label("CLIENT BODY").classes("tech-label-sub text-neutral-500 w-24 shrink-0")
            ui.label(client["body"]).classes("tech-data-mono text-neutral-400 text-xs")

    for chain_label, chain_key in [
        ("METADATA TRANSFORMS", "metadata_transforms"),
        ("OUTPUT TRANSFORMS", "output_transforms"),
        ("ID TRANSFORMS", "id_transforms"),
    ]:
        if client.get(chain_key):
            ui.label(chain_label).classes("tech-label-sub text-neutral-500")
            _render_transform_chain(client[chain_key])

    ui.separator().classes("bg-white/5")
    ui.label("SERVER RESPONSE").classes("tech-label-sub text-neutral-500 font-bold")

    if server.get("body"):
        with ui.row().classes("items-center gap-2"):
            ui.label("BODY").classes("tech-label-sub text-neutral-500 w-24 shrink-0")
            ui.label(server["body"]).classes("tech-data-mono text-neutral-400 text-xs break-all")

    if server.get("output_transforms"):
        ui.label("OUTPUT TRANSFORMS").classes("tech-label-sub text-neutral-500")
        _render_transform_chain(server["output_transforms"])


def _render_raw_entry(entry: dict):
    _render_raw_side("GET (BEACON)", entry.get("get"))
    ui.separator().classes("bg-white/10 my-2")
    _render_raw_side("POST (EXFIL)", entry.get("post"))


def _render_smb_section(section: dict):
    with ui.column().classes("w-full gap-3"):
        for label, key in [("INBOX PIPE", "inbox_pipe_name"), ("OUTBOX PIPE", "outbox_pipe_name")]:
            with ui.row().classes("items-center gap-3 py-2 border-b border-white/5"):
                ui.icon("share", size="sm", color="emerald-500").classes("opacity-60")
                ui.label(label).classes("tech-label-sub text-neutral-500 w-32 shrink-0")
                ui.label(section.get(key, "")).classes("tech-data-mono text-emerald-400")


def _render_kv_list(items: list):
    with ui.column().classes("w-full gap-0 rounded border border-white/5 overflow-hidden"):
        for item in items:
            if not isinstance(item, dict):
                continue
            for k, v in item.items():
                val_str = str(v)
                val_classes = "tech-data-mono text-xs break-all "
                val_classes += (
                    "text-amber-400"
                    if any(tok in val_str for tok in ("<METADATA>", "<CLIENT_ID>", "<OUTPUT>"))
                    else "text-neutral-400"
                )
                with ui.row().classes("w-full gap-3 px-3 py-1.5 border-b border-white/5 hover:bg-white/2"):
                    ui.label(str(k)).classes("tech-label-sub text-emerald-400/80 w-44 shrink-0")
                    ui.label(val_str).classes(val_classes)


def _render_transform_chain(steps: list):
    with ui.column().classes("w-full gap-0 rounded border border-white/5 overflow-hidden"):
        # Input row
        with ui.row().classes("items-center gap-3 px-3 py-2 bg-white/2 border-b border-white/5"):
            ui.label("INPUT").classes(
                "text-[10px] font-mono font-bold text-neutral-500 bg-white/5 border border-white/10 px-2 py-0.5 rounded w-20 text-center shrink-0"  # noqa: E501
            )
            ui.label("PREVIEW_PAYLOAD").classes("tech-data-mono text-neutral-500 text-xs")

        if not steps:
            with ui.row().classes("items-center gap-2 px-3 py-2"):
                ui.label("(no transforms — data passes through unchanged)").classes(
                    "tech-label-sub text-neutral-600 italic text-xs"
                )
            return

        for step in steps:
            with ui.row().classes("items-start gap-3 px-3 py-2 border-t border-white/5 hover:bg-white/2"):
                ui.label((step.get("op") or "").upper()).classes(
                    "text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded w-20 text-center shrink-0"  # noqa: E501
                )
                if step.get("val"):
                    ui.label(f'"{step["val"]}"').classes("tech-data-mono text-amber-400/80 text-xs shrink-0")
                ui.label(step.get("result_display", "")).classes("tech-data-mono text-neutral-300 text-xs break-all")


def _render_validation(validation: dict):
    parse_ok = validation.get("parse_ok", False)
    parse_error = validation.get("parse_error")
    missing = validation.get("missing_fields", [])
    warnings = validation.get("warnings", [])

    # Status badge
    with ui.row().classes("items-center gap-3"):
        if parse_ok:
            ui.icon("check_circle", color="emerald-500")
            ui.label("PARSE OK").classes("tech-label-sub text-emerald-400 font-bold")
        else:
            ui.icon("error", color="red-500")
            ui.label("PARSE FAILED").classes("tech-label-sub text-red-400 font-bold")

    if parse_error:
        with ui.element("div").classes("w-full bg-red-500/10 border border-red-500/20 rounded p-3"):
            ui.label(parse_error).classes("font-mono text-xs text-red-400 break-all whitespace-pre-wrap")

    if missing:
        ui.label("MISSING FIELDS").classes("tech-label-sub text-neutral-500 mt-2")
        for field in missing:
            with ui.row().classes("items-center gap-2 pl-2"):
                ui.icon("remove_circle_outline", size="xs", color="orange-400")
                ui.label(field).classes("tech-data-mono text-orange-400 text-xs")

    if warnings:
        ui.label("WARNINGS").classes("tech-label-sub text-neutral-500 mt-2")
        for w in warnings:
            with ui.row().classes("items-center gap-2 pl-2"):
                ui.icon("warning_amber", size="xs", color="amber-400")
                ui.label(w).classes("tech-label-sub text-amber-400 text-xs")

    if not parse_error and not missing and not warnings:
        with ui.row().classes("items-center gap-2 mt-2 opacity-60"):
            ui.icon("done_all", size="sm", color="emerald-500")
            ui.label("No issues detected.").classes("tech-label-sub text-neutral-500 italic")
