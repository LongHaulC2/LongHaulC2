import json
import tomllib

import structlog
from nicegui import ui

from client.modules.api_calls import (
    delete_module,
    get_all_modules,
    get_module_by_name,
    seed_modules,
    upload_module,
)
from client.pages.components.dashboard_widgets import confirm_action
from client.pages.footer import build_footer
from client.pages.formatted_tooltip import formatted_tooltip
from client.pages.menu import setup_menu
from client.utils.helpers import notify

server_log = structlog.getLogger("server")

# ════════════════════════════════════════════════════════════════════════════
#  BLANK TEMPLATES
# ════════════════════════════════════════════════════════════════════════════

_BLANK_TOML = """\
[module]
# Source filenames are auto-set to match this name (e.g. my_module.cpp, my_module.h)
name = "my_module"
display_name = "My Module"
description = ""
category = "custom"
removable = true

[sources]
files = ["my_module.cpp", "my_module.h"]

[commands.my_command]
handler = "my_handler"
args = ["arg1"]
snippet = '''
    else if (task_name == "my_command") {
        nlohmann::json result;
        std::string arg1 = task_data["task"]["args"]["arg1"];

        ModuleResult module_result = my_handler(arg1);

        result["windows_error_code"] = module_result.windows_error_code;
        result["message"] = GetErrorMessage(module_result.windows_error_code);
        result["data"] = module_result.data;
        return result;
    }
'''

[dependencies]
"""

_BLANK_CPP = """\
#include <string>
#include <windows.h>
#include "data/structs.h"
#include "my_module.h"
#include "_debug/debug.h"

ModuleResult my_handler(std::string arg1) {
    std::string output;

    // Your implementation here

    return { output, ERROR_SUCCESS };
}
"""

_BLANK_H = """\
#pragma once
#include <string>
#include "data/structs.h"
#include "_debug/debug.h"

ModuleResult my_handler(std::string arg1);
"""


# ════════════════════════════════════════════════════════════════════════════
#  TOML ↔ JSON BUNDLE CONVERSION
# ════════════════════════════════════════════════════════════════════════════


def _bundle_to_toml(bundle: dict) -> str:
    m = bundle.get("module", {})
    lines = [
        "[module]",
        f'name = "{m.get("name", "")}"',
        f'display_name = "{m.get("display_name", "")}"',
        f'description = "{m.get("description", "")}"',
        f'category = "{m.get("category", "custom")}"',
        f'removable = {"true" if m.get("removable", True) else "false"}',
        "",
    ]

    sources = bundle.get("sources", {})
    lines.append("[sources]")
    source_files = sources.get("files", [])
    lines.append(f"files = {json.dumps(source_files)}")
    libs = sources.get("libs", [])
    if libs:
        lines.append(f"libs = {json.dumps(libs)}")
    headers = sources.get("headers", [])
    if headers:
        lines.append(f"headers = {json.dumps(headers)}")
    lines.append("")

    commands = bundle.get("commands", {})
    for cmd_name, cmd in commands.items():
        lines.append(f"[commands.{cmd_name}]")
        lines.append(f'handler = "{cmd.get("handler", "")}"')
        cmd_args = cmd.get("args", [])
        lines.append(f"args = {json.dumps(cmd_args)}")
        snippet = cmd.get("snippet", "")
        lines.append("snippet = '''")
        lines.append(snippet)
        lines.append("'''")
        lines.append("")

    deps = bundle.get("dependencies", {})
    lines.append("[dependencies]")
    link_libs = deps.get("link_libs", [])
    if link_libs:
        lines.append(f"link_libs = {json.dumps(link_libs)}")

    return "\n".join(lines)


def _toml_to_bundle(toml_str: str, cpp_content: str, h_content: str) -> dict:
    data = tomllib.loads(toml_str)

    module_info = data.get("module", {})
    sources = data.get("sources", {})
    commands = data.get("commands", {})
    deps = data.get("dependencies", {})

    name = module_info.get("name", "module")

    # The build system generates #include "modules/<name>/<name>.h" from the
    # module name, so source filenames MUST match [module] name.
    cpp_filename = f"{name}.cpp"
    h_filename = f"{name}.h"
    sources["files"] = [cpp_filename, h_filename]

    return {
        "module": module_info,
        "sources": sources,
        "commands": commands,
        "dependencies": deps,
        "files": {
            cpp_filename: cpp_content,
            h_filename: h_content,
        },
    }


def _extract_files_from_bundle(bundle: dict) -> tuple[str, str]:
    files = bundle.get("files", {})
    cpp_content = ""
    h_content = ""
    for filename, content in files.items():
        if filename.endswith(".cpp"):
            cpp_content = content
        elif filename.endswith(".h"):
            h_content = content
    return cpp_content, h_content


# ════════════════════════════════════════════════════════════════════════════
#  STATE
# ════════════════════════════════════════════════════════════════════════════


class _ModuleBuilderState:
    def __init__(self):
        # module_name -> {toml, cpp, h, original_toml, original_cpp, original_h}
        self.modules: dict[str, dict] = {}

        # tab key "module::filetype" -> {tab_object, panel_object, editor}
        self.open_tabs: dict[str, dict] = {}

        self.tabs = None
        self.panels = None
        self.module_names: list[str] = []
        self.active_tab_key: str | None = None


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════


def _tab_key(module_name: str, file_type: str) -> str:
    return f"{module_name}::{file_type}"


def _file_display(module_name: str, file_type: str) -> str:
    if file_type == "toml":
        return f"{module_name} - config.toml"
    if file_type == "cpp":
        return f"{module_name} - {module_name}.cpp"
    return f"{module_name} - {module_name}.h"


def _tree_file(label: str, is_active: bool, on_click):
    bg = " bg-white/5 text-zinc-200" if is_active else ""
    ui.label(label).classes(
        "w-full text-[11px] font-mono text-zinc-500 pl-8 py-2 cursor-pointer "
        "hover:bg-white/5 hover:text-zinc-300 transition-colors" + bg
    ).on("click", on_click)


def _is_dirty(state: _ModuleBuilderState, module_name: str) -> bool:
    mod = state.modules.get(module_name)
    if not mod:
        return False
    for ft in ("toml", "cpp", "h"):
        key = _tab_key(module_name, ft)
        tab_data = state.open_tabs.get(key)
        current = tab_data["editor"].value if tab_data and tab_data["editor"] else mod[ft]
        if current != mod[f"original_{ft}"]:
            return True
    return False


def _get_active_module(state: _ModuleBuilderState) -> str | None:
    if not state.active_tab_key:
        return None
    return state.active_tab_key.split("::")[0]


async def _fetch_module_names() -> list[str]:
    try:
        resp = await get_all_modules()
        if resp and resp.get("data"):
            return sorted([m["artifact_name"] for m in resp["data"]], key=str.lower)
    except Exception:
        pass
    return []


async def _load_module(state: _ModuleBuilderState, module_name: str):
    if module_name in state.modules:
        return True
    resp = await get_module_by_name(module_name)
    if not (resp and resp.get("data", {}).get("artifact_contents")):
        notify(f"Failed to load {module_name}", type="negative")
        return False
    try:
        bundle = json.loads(resp["data"]["artifact_contents"])
    except json.JSONDecodeError:
        notify("Invalid module JSON", type="negative")
        return False

    toml_str = _bundle_to_toml(bundle)
    cpp_content, h_content = _extract_files_from_bundle(bundle)
    state.modules[module_name] = {
        "toml": toml_str,
        "cpp": cpp_content,
        "h": h_content,
        "original_toml": toml_str,
        "original_cpp": cpp_content,
        "original_h": h_content,
    }
    return True


# ════════════════════════════════════════════════════════════════════════════
#  PAGE
# ════════════════════════════════════════════════════════════════════════════


@ui.page("/module-builder")
async def module_builder_page():
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    setup_menu("Module Builder")
    await _module_builder_view()
    await build_footer()


async def _module_builder_view():
    state = _ModuleBuilderState()
    state.module_names = await _fetch_module_names()

    # ── Tab management ────────────────────────────────────────────────

    async def open_file(module_name: str, file_type: str):
        key = _tab_key(module_name, file_type)

        if key in state.open_tabs:
            state.panels.set_value(key)
            state.active_tab_key = key
            return

        if not await _load_module(state, module_name):
            return

        content = state.modules[module_name][file_type]
        language = "TOML" if file_type == "toml" else "C++"
        tab_label = _file_display(module_name, file_type)

        with state.tabs, ui.tab(name=key, label="").classes(  # noqa: SIM117
            "h-full px-3 min-h-0 border-r border-white/5"
        ) as tab:
            with ui.row().classes("items-center gap-2"):
                ui.label(tab_label).classes("tech-label-sub")
                ui.button(
                    icon="close",
                    on_click=lambda k=key: close_tab(k),
                ).props("flat dense square size=sm").classes("text-neutral-600 hover:text-red-400")

        with state.panels, ui.tab_panel(name=key).classes("p-0 w-full h-full") as panel:
            editor = ui.codemirror(
                content,
                language=language,
                theme="androidstudio",
            ).classes("w-full h-full min-h-[400px]")

            editor.on_value_change(lambda e, mn=module_name, ft=file_type: _on_editor_change(state, mn, ft, e.value))

        state.open_tabs[key] = {"tab_object": tab, "panel_object": panel, "editor": editor}
        state.panels.set_value(key)
        state.active_tab_key = key

    def close_tab(key: str):
        tab_data = state.open_tabs.pop(key, None)
        if not tab_data:
            return
        state.tabs.remove(tab_data["tab_object"])
        state.panels.remove(tab_data["panel_object"])

        if not state.open_tabs:
            state.panels.set_value(None)
            state.active_tab_key = None
        elif state.active_tab_key == key:
            last_key = list(state.open_tabs.keys())[-1]
            state.panels.set_value(last_key)
            state.active_tab_key = last_key

    def close_all_module_tabs(module_name: str):
        for ft in ("toml", "cpp", "h"):
            close_tab(_tab_key(module_name, ft))

    # ── Action handlers ───────────────────────────────────────────────

    async def do_save():
        active_mod = _get_active_module(state)
        if not active_mod:
            notify("No module open to save", type="warning", color="orange-9")
            return

        mod = state.modules.get(active_mod)
        if not mod:
            return

        _sync_editors_to_state(state, active_mod)

        try:
            bundle = _toml_to_bundle(mod["toml"], mod["cpp"], mod["h"])
        except Exception as ex:
            notify(f"TOML parse error: {ex}", type="negative")
            return

        actual_name = bundle.get("module", {}).get("name", "").strip()
        if not actual_name:
            notify("Module name is empty — set [module] name in config", type="warning", color="orange-9")
            return

        resp = await upload_module(actual_name, json.dumps(bundle))
        if not resp:
            notify("Save failed", type="negative")
            return

        if active_mod != actual_name:
            await _migrate_module(state, active_mod, actual_name, open_file)
        else:
            mod["original_toml"] = mod["toml"]
            mod["original_cpp"] = mod["cpp"]
            mod["original_h"] = mod["h"]

        state.module_names = await _fetch_module_names()
        render_tree.refresh()
        notify(f"Saved '{actual_name}'", type="positive", color="emerald-9")

    async def do_save_as():
        active_mod = _get_active_module(state)
        if not active_mod:
            notify("No module open to save", type="warning", color="orange-9")
            return

        mod = state.modules.get(active_mod)
        if not mod:
            return

        _sync_editors_to_state(state, active_mod)

        try:
            bundle = _toml_to_bundle(mod["toml"], mod["cpp"], mod["h"])
        except Exception as ex:
            notify(f"TOML parse error: {ex}", type="negative")
            return

        default_name = bundle.get("module", {}).get("name", "my_module")

        with ui.dialog() as d, ui.card().classes("tech-dialog w-96 p-0 rounded overflow-hidden"):
            with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
                ui.label("SAVE AS").classes("tech-label-sub")
                ui.button(icon="close", on_click=d.close).props("dense flat size=sm color=grey")

            with ui.column().classes("p-4 gap-4 w-full"):
                name_input = (
                    ui.input("MODULE NAME", value=default_name)
                    .props("outlined dense dark color=emerald")
                    .classes("w-full tech-input")
                )

            with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"):
                ui.button("CANCEL", on_click=d.close).props("flat dense color=grey no-caps")

                async def finalize():
                    save_name = (name_input.value or "").strip()
                    if not save_name:
                        notify("Enter a module name", type="warning", color="orange-9")
                        return
                    bundle["module"]["name"] = save_name
                    resp = await upload_module(save_name, json.dumps(bundle))
                    if not resp:
                        notify("Save failed", type="negative")
                        return
                    d.close()

                    cpp_content, h_content = _extract_files_from_bundle(bundle)
                    toml_str = _bundle_to_toml(bundle)
                    state.modules[save_name] = {
                        "toml": toml_str,
                        "cpp": cpp_content,
                        "h": h_content,
                        "original_toml": toml_str,
                        "original_cpp": cpp_content,
                        "original_h": h_content,
                    }

                    state.module_names = await _fetch_module_names()
                    render_tree.refresh()
                    await open_file(save_name, "toml")
                    notify(f"Saved '{save_name}'", type="positive", color="emerald-9")

                ui.button("SAVE", on_click=finalize).props("unelevated dense color=emerald no-caps")

        d.open()

    def do_new():
        with ui.dialog() as d, ui.card().classes("tech-dialog w-96 p-0 rounded overflow-hidden"):
            with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
                ui.label("NEW MODULE").classes("tech-label-sub")
                ui.button(icon="close", on_click=d.close).props("dense flat size=sm color=grey")

            with ui.column().classes("p-4 gap-4 w-full"):
                name_input = (
                    ui.input("MODULE NAME", placeholder="e.g. my_module")
                    .props("outlined dense dark color=emerald autofocus")
                    .classes("w-full tech-input")
                )

            with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"):
                ui.button("CANCEL", on_click=d.close).props("flat dense color=grey no-caps")

                async def create():
                    mod_name = (name_input.value or "").strip()
                    if not mod_name:
                        notify("Enter a module name", type="warning", color="orange-9")
                        return

                    toml = _BLANK_TOML.replace("my_module", mod_name).replace(
                        "My Module", mod_name.replace("_", " ").title()
                    )
                    cpp = _BLANK_CPP.replace("my_module", mod_name)
                    h = _BLANK_H.replace("my_module", mod_name)

                    try:
                        bundle = _toml_to_bundle(toml, cpp, h)
                    except Exception as ex:
                        notify(f"Template error: {ex}", type="negative")
                        return

                    resp = await upload_module(mod_name, json.dumps(bundle))
                    if not resp:
                        notify("Create failed", type="negative")
                        return

                    d.close()
                    state.modules[mod_name] = {
                        "toml": toml,
                        "cpp": cpp,
                        "h": h,
                        "original_toml": toml,
                        "original_cpp": cpp,
                        "original_h": h,
                    }
                    state.module_names = await _fetch_module_names()
                    render_tree.refresh()
                    await open_file(mod_name, "toml")
                    notify(f"Created '{mod_name}'", type="positive", color="emerald-9")

                ui.button("CREATE", on_click=create).props("unelevated dense color=emerald no-caps")

        d.open()

    async def do_delete(module_name: str):
        close_all_module_tabs(module_name)

        resp = await delete_module(module_name)
        if not resp:
            notify("Delete failed", type="negative")
            return

        state.modules.pop(module_name, None)
        state.module_names = await _fetch_module_names()
        render_tree.refresh()
        notify(f"Deleted '{module_name}'", type="positive", color="emerald-9")

    def do_delete_active():
        active_mod = _get_active_module(state)
        if not active_mod:
            notify("No module open to delete", type="warning", color="orange-9")
            return
        confirm_action(
            title="DELETE MODULE",
            message=f"Delete '{active_mod}'?",
            on_confirm=lambda: do_delete(active_mod),
            confirm_label="DELETE",
            icon="delete",
        )

    async def do_duplicate():
        active_mod = _get_active_module(state)
        if not active_mod:
            notify("No module open to duplicate", type="warning", color="orange-9")
            return

        mod = state.modules.get(active_mod)
        if not mod:
            if not await _load_module(state, active_mod):
                return
            mod = state.modules[active_mod]

        _sync_editors_to_state(state, active_mod)
        dup_name = f"{active_mod}_duplicate"

        toml = mod["toml"].replace(active_mod, dup_name)
        cpp = mod["cpp"].replace(active_mod, dup_name)
        h = mod["h"].replace(active_mod, dup_name)

        try:
            bundle = _toml_to_bundle(toml, cpp, h)
        except Exception as ex:
            notify(f"TOML parse error: {ex}", type="negative")
            return

        resp = await upload_module(dup_name, json.dumps(bundle))
        if not resp:
            notify("Duplicate failed", type="negative")
            return

        state.modules[dup_name] = {
            "toml": toml,
            "cpp": cpp,
            "h": h,
            "original_toml": toml,
            "original_cpp": cpp,
            "original_h": h,
        }
        state.module_names = await _fetch_module_names()
        render_tree.refresh()
        await open_file(dup_name, "toml")
        notify(f"Duplicated as '{dup_name}'", type="positive", color="emerald-9")

    async def do_seed():
        resp = await seed_modules()
        if resp and resp.get("data"):
            d = resp["data"]
            notify(
                f"Seeded: {d.get('created', 0)} new, {d.get('updated', 0)} updated",
                type="positive",
                color="emerald-9",
            )
            state.module_names = await _fetch_module_names()
            render_tree.refresh()
        else:
            notify("Seed failed", type="negative")

    async def do_refresh():
        state.module_names = await _fetch_module_names()
        render_tree.refresh()

    def on_tab_change(e):
        state.active_tab_key = e.value or None

    # ── Tree rendering ────────────────────────────────────────────────

    @ui.refreshable
    def render_tree():
        if not state.module_names:
            with ui.column().classes("tech-empty-state w-full py-12"):
                ui.icon("extension", size="xl", color="emerald-500")
                ui.label("No modules — seed defaults or create new").classes("tech-label-sub text-neutral-500")
            return

        for mod_name in state.module_names:
            dirty = _is_dirty(state, mod_name)

            with ui.expansion(icon="folder").classes("w-full tech-expansion") as exp:
                with exp.add_slot("header"), ui.row().classes("items-center gap-2 w-full"):
                    ui.label(mod_name).style("font-weight: 500")
                    if dirty:
                        ui.element("div").classes("w-2 h-2 rounded-full bg-emerald-400").style("flex-shrink: 0")

                _tree_file(
                    "config.toml",
                    state.active_tab_key == _tab_key(mod_name, "toml"),
                    lambda _e, mn=mod_name: open_file(mn, "toml"),
                )
                _tree_file(
                    f"{mod_name}.cpp",
                    state.active_tab_key == _tab_key(mod_name, "cpp"),
                    lambda _e, mn=mod_name: open_file(mn, "cpp"),
                )
                _tree_file(
                    f"{mod_name}.h",
                    state.active_tab_key == _tab_key(mod_name, "h"),
                    lambda _e, mn=mod_name: open_file(mn, "h"),
                )

    # ══════════════════════════════════════════════════════════════════
    #  MAIN LAYOUT
    # ══════════════════════════════════════════════════════════════════

    with ui.element().classes("w-full h-full gap-0"):  # noqa: SIM117
        with ui.splitter(value=25, limits=(15, 40)).classes("w-full h-full").props(
            "separator-class=bg-white/10 separator-style=width:1px"
        ) as splitter:
            # ── LEFT PANE: File Tree ──────────────────────────────────
            with splitter.before:  # noqa: SIM117
                with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
                    with ui.row().classes(  # noqa: SIM117
                        "w-full items-center justify-between tech-header-bar px-4 shrink-0"
                    ):
                        with ui.row().classes("items-center gap-3"):
                            ui.icon("extension", color="emerald-500").classes("text-xl")
                            ui.label("MODULES //").classes("tech-label-header-section")

                    with ui.row().classes("w-full items-center gap-1 px-3 py-2 border-b border-white/5 shrink-0"):
                        with (
                            ui.button(icon="note_add", on_click=do_new)
                            .props("flat dense size=sm")
                            .classes("tech-btn-action")
                        ):
                            formatted_tooltip("New Module")
                        with (
                            ui.button(icon="refresh", on_click=do_refresh)
                            .props("flat dense size=sm")
                            .classes("tech-btn-secondary")
                        ):
                            formatted_tooltip("Refresh")

                        if not state.module_names:
                            ui.separator().classes("bg-white/10 h-4 w-[1px] mx-1")
                            with (
                                ui.button(icon="cloud_download", on_click=do_seed)
                                .props("flat dense size=sm")
                                .classes("tech-btn-action-2")
                            ):
                                formatted_tooltip("Seed Default Modules")

                    with ui.scroll_area().classes("w-full flex-grow"), ui.column().classes(  # noqa: SIM117
                        "w-full gap-0 p-1"
                    ):
                        render_tree()

            # ── RIGHT PANE: Tabbed Editor ─────────────────────────────
            with splitter.after:  # noqa: SIM117
                with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
                    with ui.row().classes(
                        "w-full items-center justify-between bg-black/20 "
                        "border-b border-white/5 px-2 h-10 gap-2 shrink-0"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("code", size="xs", color="emerald-500")
                            ui.label("EDITOR //").classes("tech-label-sub")

                        state.tabs = ui.tabs().props(
                            "dense indicator-color=emerald text-color=grey-5 "
                            "active-color=emerald-400 narrow-indicator align=left"
                        )
                        state.tabs.classes("bg-transparent h-full flex-grow")
                        state.tabs.on_value_change(on_tab_change)

                        ui.separator().classes("bg-white/10 h-4 w-[1px] mx-1")

                        with ui.row().classes("items-center gap-1"):
                            with (
                                ui.button(icon="save", on_click=do_save)
                                .props("flat dense size=sm")
                                .classes("tech-btn-action")
                            ):
                                formatted_tooltip("Save Module")
                            with (
                                ui.button(icon="save_as", on_click=do_save_as)
                                .props("flat dense size=sm")
                                .classes("tech-btn-secondary")
                            ):
                                formatted_tooltip("Save As")
                            with (
                                ui.button(icon="content_copy", on_click=do_duplicate)
                                .props("flat dense size=sm")
                                .classes("tech-btn-secondary")
                            ):
                                formatted_tooltip("Duplicate Module")
                            with (
                                ui.button(icon="delete", on_click=do_delete_active)
                                .props("flat dense size=sm")
                                .classes("tech-btn-destructive")
                            ):
                                formatted_tooltip("Delete Module")

                    state.panels = (
                        ui.tab_panels(state.tabs)
                        .classes("w-full h-full bg-neutral-900/40")
                        .props("dense transition-duration=0")
                    )


# ════════════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ════════════════════════════════════════════════════════════════════════════


def _on_editor_change(state: _ModuleBuilderState, module_name: str, file_type: str, value: str):
    mod = state.modules.get(module_name)
    if mod:
        mod[file_type] = value


def _sync_editors_to_state(state: _ModuleBuilderState, module_name: str):
    for ft in ("toml", "cpp", "h"):
        key = _tab_key(module_name, ft)
        tab_data = state.open_tabs.get(key)
        if tab_data and tab_data["editor"]:
            state.modules[module_name][ft] = tab_data["editor"].value


async def _migrate_module(state: _ModuleBuilderState, old_name: str, new_name: str, open_file_fn):
    open_types = [ft for ft in ("toml", "cpp", "h") if _tab_key(old_name, ft) in state.open_tabs]

    for ft in ("toml", "cpp", "h"):
        key = _tab_key(old_name, ft)
        tab_data = state.open_tabs.pop(key, None)
        if tab_data:
            state.tabs.remove(tab_data["tab_object"])
            state.panels.remove(tab_data["panel_object"])

    if not state.open_tabs:
        state.panels.set_value(None)
        state.active_tab_key = None

    mod = state.modules.pop(old_name, None)
    if mod:
        mod["original_toml"] = mod["toml"]
        mod["original_cpp"] = mod["cpp"]
        mod["original_h"] = mod["h"]
        state.modules[new_name] = mod

    for ft in open_types:
        await open_file_fn(new_name, ft)
