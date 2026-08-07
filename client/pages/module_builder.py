import json
import tomllib

import structlog
from nicegui import ui

from client.modules.api_calls import (
    get_all_modules,
    get_module_by_name,
    seed_modules,
    upload_module,
)
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
        self.toml_editor = None
        self.cpp_editor = None
        self.h_editor = None
        self.preview_viewer = None
        self.preview_title = None
        self.current_module_name: str | None = None
        self.module_select = None


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

    module_names = await _fetch_module_names()

    # ── Action handlers ───────────────────────────────────────────────

    def do_preview():
        toml_str = state.toml_editor.value if state.toml_editor else ""
        cpp_str = state.cpp_editor.value if state.cpp_editor else ""
        h_str = state.h_editor.value if state.h_editor else ""

        try:
            bundle = _toml_to_bundle(toml_str, cpp_str, h_str)
        except Exception as ex:
            _set_preview(state, "ERROR", f"TOML parse error:\n{ex}")
            notify(f"TOML parse error: {ex}", type="negative")
            return

        pretty = json.dumps(bundle, indent=2)
        _set_preview(state, "MODULE_BUNDLE", pretty)
        notify("Bundle preview generated", type="positive", color="emerald-9")

    async def do_save():
        toml_str = state.toml_editor.value if state.toml_editor else ""
        cpp_str = state.cpp_editor.value if state.cpp_editor else ""
        h_str = state.h_editor.value if state.h_editor else ""

        try:
            bundle = _toml_to_bundle(toml_str, cpp_str, h_str)
        except Exception as ex:
            notify(f"TOML parse error: {ex}", type="negative")
            return

        module_name = bundle.get("module", {}).get("name", "").strip()
        if not module_name:
            notify("Module name is empty — set [module] name in config", type="warning", color="orange-9")
            return

        resp = await upload_module(module_name, json.dumps(bundle))
        if resp:
            state.current_module_name = module_name
            await refresh_modules()
            state.module_select.set_value(module_name)
            _set_preview(state, "MODULE_BUNDLE", json.dumps(bundle, indent=2))
            notify(f"Saved '{module_name}'", type="positive", color="emerald-9")
        else:
            notify("Save failed", type="negative")

    async def do_save_as():
        toml_str = state.toml_editor.value if state.toml_editor else ""
        cpp_str = state.cpp_editor.value if state.cpp_editor else ""
        h_str = state.h_editor.value if state.h_editor else ""

        try:
            bundle = _toml_to_bundle(toml_str, cpp_str, h_str)
        except Exception as ex:
            notify(f"TOML parse error: {ex}", type="negative")
            return

        default_name = bundle.get("module", {}).get("name", "my_module")

        with ui.dialog() as d, ui.card().classes("tech-dialog w-96 p-0 rounded overflow-hidden"):
            with ui.row().classes("w-full bg-neutral-900/50 p-4 border-b border-white/5 items-center justify-between"):
                ui.label("SAVE_AS").classes("tech-label-sub")
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
                    state.current_module_name = save_name
                    d.close()
                    await refresh_modules()
                    state.module_select.set_value(save_name)
                    notify(f"Saved '{save_name}'", type="positive", color="emerald-9")

                ui.button("SAVE", on_click=finalize).props("unelevated dense color=emerald no-caps")

        d.open()

    def do_new():
        if state.toml_editor:
            state.toml_editor.value = _BLANK_TOML
        if state.cpp_editor:
            state.cpp_editor.value = _BLANK_CPP
        if state.h_editor:
            state.h_editor.value = _BLANK_H
        state.current_module_name = None
        if state.module_select:
            state.module_select.set_value(None)
        _set_preview(state, "INSPECTOR", "// New module — edit the config, source, and header tabs.")
        notify("New module started", type="info")

    async def on_module_select(e):
        if not e.value:
            return
        resp = await get_module_by_name(e.value)
        if resp and resp.get("data", {}).get("artifact_contents"):
            try:
                bundle = json.loads(resp["data"]["artifact_contents"])
            except json.JSONDecodeError:
                notify("Invalid module JSON", type="negative")
                return

            toml_str = _bundle_to_toml(bundle)
            cpp_content, h_content = _extract_files_from_bundle(bundle)

            if state.toml_editor:
                state.toml_editor.value = toml_str
            if state.cpp_editor:
                state.cpp_editor.value = cpp_content
            if state.h_editor:
                state.h_editor.value = h_content

            state.current_module_name = e.value
            _set_preview(state, f"MODULE: {e.value}", json.dumps(bundle, indent=2))
            notify(f"Loaded {e.value}", type="positive", color="emerald-9")
        else:
            notify(f"Failed to load {e.value}", type="negative")

    async def refresh_modules():
        nonlocal module_names
        module_names = await _fetch_module_names()
        if state.module_select:
            state.module_select.options = module_names
            state.module_select.update()

    async def do_seed():
        resp = await seed_modules()
        if resp and resp.get("data"):
            d = resp["data"]
            notify(
                f"Seeded: {d.get('created', 0)} new, {d.get('updated', 0)} updated",
                type="positive",
                color="emerald-9",
            )
            await refresh_modules()
        else:
            notify("Seed failed", type="negative")

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
                            ui.icon("extension", color="emerald-500").classes("text-xl")
                            ui.label("MODULE_BUILDER //").classes("tech-label-header-section")

                    # Module selector row
                    with ui.row().classes("w-full items-center gap-2 px-3 pt-3 pb-1 shrink-0"):
                        state.module_select = (
                            ui.select(
                                options=module_names,
                                label="Load Existing Module",
                                value=None,
                                on_change=on_module_select,
                            )
                            .props("outlined dense dark color=emerald options-dense clearable")
                            .classes("flex-grow tech-select")
                        )
                        with (
                            ui.button(icon="refresh", on_click=refresh_modules)
                            .props("flat dense size=xs")
                            .classes("tech-btn-secondary")
                        ):
                            formatted_tooltip("Refresh List")

                    # Seed banner
                    if not module_names:
                        with ui.row().classes(
                            "w-full items-center gap-2 px-3 py-2 bg-amber-500/10 border-b border-amber-500/20"
                        ):
                            ui.icon("info", size="xs", color="amber-400")
                            ui.label("No modules on server.").classes("tech-label-sub text-amber-400 text-xs")
                            ui.button("SEED DEFAULTS", on_click=do_seed).props("flat dense size=xs color=amber no-caps")

                    # Editor tabs
                    with ui.scroll_area().classes("w-full flex-grow"), ui.column().classes(  # noqa: SIM117
                        "w-full h-full gap-0"
                    ):
                        with ui.tabs().classes("w-full shrink-0").props(
                            "dense active-color=emerald indicator-color=emerald text-color=grey-5"
                        ) as editor_tabs:
                            config_tab = ui.tab("CONFIG (.toml)")
                            source_tab = ui.tab("SOURCE (.cpp)")
                            header_tab = ui.tab("HEADER (.h)")

                        with ui.tab_panels(editor_tabs, value=config_tab).classes("w-full flex-grow overflow-auto"):
                            with ui.tab_panel(config_tab).classes("p-0"):
                                state.toml_editor = ui.codemirror(
                                    _BLANK_TOML,
                                    language="TOML",
                                    theme="androidstudio",
                                ).classes("w-full h-full min-h-[400px]")

                            with ui.tab_panel(source_tab).classes("p-0"):
                                state.cpp_editor = ui.codemirror(
                                    _BLANK_CPP,
                                    language="C++",
                                    theme="androidstudio",
                                ).classes("w-full h-full min-h-[400px]")

                            with ui.tab_panel(header_tab).classes("p-0"):
                                state.h_editor = ui.codemirror(
                                    _BLANK_H,
                                    language="C++",
                                    theme="androidstudio",
                                ).classes("w-full h-full min-h-[400px]")

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
                                formatted_tooltip("New Module")
                            with (
                                ui.button(icon="save", on_click=do_save)
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

                        ui.button(
                            "PREVIEW",
                            icon="preview",
                            on_click=do_preview,
                        ).props("unelevated dense no-caps size=sm").classes(
                            "bg-emerald-600 text-white font-bold tracking-wide text-xs px-4"
                        )

            with splitter.after:  # noqa: SIM117
                with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
                    with ui.row().classes("w-full items-center gap-3 tech-header-bar px-4 shrink-0"):
                        ui.icon("code", color="emerald-500").classes("text-xl")
                        state.preview_title = ui.label("INSPECTOR //").classes("tech-label-header-section")

                    state.preview_viewer = (
                        ui.codemirror(
                            "// Edit the config, source, and header tabs, then click PREVIEW\n"
                            "// to see the generated JSON module bundle here.",
                            language="JSON",
                            theme="androidstudio",
                        )
                        .classes("w-full h-full min-h-[400px]")
                        .props("readonly")
                    )


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════


def _set_preview(state: _ModuleBuilderState, title: str, content: str):
    if state.preview_title:
        state.preview_title.set_text(f"{title} //")
    if state.preview_viewer:
        state.preview_viewer.value = content


async def _fetch_module_names() -> list[str]:
    try:
        resp = await get_all_modules()
        if resp and resp.get("data"):
            return sorted([m["artifact_name"] for m in resp["data"]], key=str.lower)
    except Exception:
        pass
    return []
