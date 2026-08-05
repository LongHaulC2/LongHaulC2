import json

import structlog
from nicegui import ui

from client.modules.api_calls import (
    build_implant,
    get_all_build_configs,
    get_all_listener_data,
    get_all_modules,
    get_all_templates,
    get_build_config_by_name,
    get_module_by_name,
    save_build_config,
    seed_modules,
)
from client.pages.footer import build_footer
from client.pages.formatted_tooltip import formatted_tooltip
from client.pages.menu import setup_menu
from client.utils.helpers import notify

server_log = structlog.getLogger("server")
server_log.info("Loading /builder page")


class _BuilderState:
    def __init__(self):
        self.templates: list[dict] = []
        self.all_modules: list[dict] = []
        self.listeners: list[dict] = []

        self.selected_template: str = "win_x64"
        self.selected_modules: list[str] = []
        self.default_modules: list[str] = []
        self.required_modules: set[str] = set()

        self.implant_name: str = ""
        self.callback_host: str = ""
        self.selected_listeners: list[str] = []
        self.init_get_listener: str | None = None
        self.init_post_listener: str | None = None

        self.debug_enabled: bool = False
        self.clear_cache: bool = False

        self.code_viewer = None
        self.code_title_label = None
        self.module_card = None


@ui.page("/builder")
async def builder_page():
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )
    setup_menu("Builder")
    await _builder_view()
    await build_footer()


async def _builder_view():
    state = _BuilderState()

    templates_resp = await get_all_templates()
    if templates_resp and templates_resp.get("data"):
        state.templates = templates_resp["data"]
        if state.templates:
            first = state.templates[0]
            state.selected_template = first.get("name", "win_x64")
            state.default_modules = first.get("build", {}).get("default_modules", [])
            state.selected_modules = list(state.default_modules)

    modules_resp = await get_all_modules()
    if modules_resp and modules_resp.get("data"):
        state.all_modules = modules_resp["data"]
        for mod in state.all_modules:
            detail = await get_module_by_name(mod["artifact_name"])
            if detail and detail.get("data", {}).get("artifact_contents"):
                try:
                    bundle = json.loads(detail["data"]["artifact_contents"])
                    if not bundle.get("module", {}).get("removable", True):
                        state.required_modules.add(mod["artifact_name"])
                except json.JSONDecodeError:
                    pass

    listeners_resp = await get_all_listener_data()
    if listeners_resp and listeners_resp.get("data"):
        state.listeners = listeners_resp["data"]

    @ui.refreshable
    def editor_panel():
        with ui.column().classes("w-full h-full gap-0"):
            with ui.tabs().classes("w-full shrink-0").props(
                "dense active-color=emerald indicator-color=emerald text-color=grey-5"
            ) as main_tabs:
                implant_tab = ui.tab("IMPLANT")
                loader_tab = ui.tab("LOADER")
                profiles_tab = ui.tab("PROFILES")
                misc_tab = ui.tab("MISC")

            with ui.tab_panels(main_tabs, value=implant_tab).classes("w-full flex-grow overflow-auto"):
                with ui.tab_panel(implant_tab):
                    _implant_tab(state)
                with ui.tab_panel(loader_tab):
                    _loader_tab()
                with ui.tab_panel(profiles_tab):
                    _profiles_tab(state)
                with ui.tab_panel(misc_tab):
                    _misc_tab(state)

    with ui.element().classes("w-full h-full gap-0"):  # noqa: SIM117
        with ui.splitter(value=42, limits=(25, 65)).classes("w-full h-full").props(
            "separator-class=bg-white/10 separator-style=width:1px"
        ) as splitter:
            with splitter.before:  # noqa: SIM117
                with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):  # noqa: SIM117
                    with ui.row().classes(  # noqa: SIM117
                        "w-full items-center justify-between tech-header-bar px-4 shrink-0"
                    ):
                        with ui.row().classes("items-center gap-3"):
                            ui.icon("construction", color="emerald-500").classes("text-xl")
                            ui.label("IMPLANT_BUILDER //").classes("tech-label-header-section")

                    with ui.scroll_area().classes("w-full flex-grow"):
                        editor_panel()

                    with ui.row().classes(
                        "w-full items-center justify-between px-3 py-2 border-t "
                        "border-white/5 bg-black/20 shrink-0 gap-2"
                    ):
                        with ui.row().classes("items-center gap-1"):

                            async def do_save_config_quick():
                                config_data = _build_config_json(state)
                                name = state.implant_name or "untitled"
                                resp = await save_build_config(name, config_data)
                                if resp:
                                    notify(f"Config '{name}' saved", type="positive", color="emerald-9")
                                else:
                                    notify("Save failed", type="negative")

                            with (
                                ui.button(icon="save", on_click=do_save_config_quick)
                                .props("flat dense size=sm")
                                .classes("tech-btn-secondary")
                            ):
                                formatted_tooltip("Quick Save Config")

                            async def do_load_config_dialog():
                                resp = await get_all_build_configs()
                                if not resp or not resp.get("data"):
                                    notify("No saved configs found", type="info")
                                    return
                                configs = resp["data"]
                                with ui.dialog() as dlg, ui.card().classes(
                                    "tech-dialog w-[500px] p-0 rounded overflow-hidden"
                                ):
                                    with ui.row().classes(
                                        "w-full bg-neutral-900/50 p-4 border-b border-white/5 "
                                        "items-center justify-between"
                                    ):
                                        ui.label("LOAD CONFIG").classes("tech-label-sub")
                                        ui.button(icon="close", on_click=dlg.close).props(
                                            "dense flat size=sm color=grey"
                                        )
                                    with ui.column().classes("p-4 gap-2 w-full"):
                                        for cfg in configs:

                                            async def load_one(cfg_name=cfg["artifact_name"]):
                                                detail = await get_build_config_by_name(cfg_name)
                                                if detail and detail.get("data", {}).get("artifact_contents"):
                                                    _apply_config(state, detail["data"]["artifact_contents"])
                                                    dlg.close()
                                                    editor_panel.refresh()
                                                    notify(f"Loaded '{cfg_name}'", type="positive", color="emerald-9")

                                            ui.button(
                                                cfg["artifact_name"],
                                                on_click=load_one,
                                            ).props("flat dense no-caps color=emerald").classes("w-full text-left")
                                dlg.open()

                            with (
                                ui.button(icon="folder_open", on_click=do_load_config_dialog)
                                .props("flat dense size=sm")
                                .classes("tech-btn-secondary")
                            ):
                                formatted_tooltip("Load Config")

                        async def do_build():
                            if not state.implant_name:
                                notify("Set an implant name (Misc tab)", type="warning", color="orange-9")
                                return
                            if not state.selected_listeners:
                                notify("Add at least one listener (Profiles tab)", type="warning", color="orange-9")
                                return
                            if not state.init_get_listener or not state.init_post_listener:
                                notify(
                                    "Set initial GET and POST listeners (Profiles tab)",
                                    type="warning",
                                    color="orange-9",
                                )
                                return
                            if not state.callback_host:
                                notify("Set a callback host (Profiles tab)", type="warning", color="orange-9")
                                return

                            _set_code_viewer(state, "BUILD_OUTPUT", "Submitting build...")
                            notify("Build submitted", type="info")

                            resp = await build_implant(
                                implant_name=state.implant_name,
                                listener_uuids=state.selected_listeners,
                                initial_get_profile_listener_uuid=state.init_get_listener,
                                initial_post_profile_listener_uuid=state.init_post_listener,
                                callback_host=state.callback_host,
                                template_name=state.selected_template,
                                modules=state.selected_modules or None,
                                options={
                                    "debug": state.debug_enabled,
                                    "clear_cache": state.clear_cache,
                                },
                            )

                            if resp and resp.get("data"):
                                data = resp["data"]
                                build_uuid = data.get("build_uuid", "unknown")
                                stats = data.get("build_stats", {})
                                build_time = stats.get("build_time", 0)
                                output = (
                                    f"Build complete.\n\n"
                                    f"Build UUID:  {build_uuid}\n"
                                    f"Build Time:  {build_time:.2f}s\n"
                                    f"Template:    {state.selected_template}\n"
                                    f"Modules:     {', '.join(state.selected_modules)}\n"
                                )
                                _set_code_viewer(state, "BUILD_RESULT", output)
                                notify(f"Build complete — {build_time:.1f}s", type="positive", color="emerald-9")
                            else:
                                msg = resp.get("message", "Unknown error") if resp else "No response"
                                _set_code_viewer(state, "BUILD_RESULT", f"Build failed: {msg}")
                                notify("Build failed", type="negative")

                        ui.button(
                            "BUILD",
                            icon="rocket_launch",
                            on_click=do_build,
                        ).props("unelevated dense no-caps size=sm").classes(
                            "bg-emerald-600 text-white font-bold tracking-wide text-xs px-4"
                        )

            with splitter.after:  # noqa: SIM117
                with ui.column().classes("w-full h-full gap-0 tech-glass-panel"):
                    with ui.row().classes("w-full items-center gap-3 tech-header-bar px-4 shrink-0"):
                        ui.icon("code", color="emerald-500").classes("text-xl")
                        state.code_title_label = ui.label("INSPECTOR //").classes("tech-label-header-section")

                    state.code_viewer = (
                        ui.codemirror(
                            "// Select a module or build to see details here.",
                            language="C++",
                            theme="androidstudio",
                        )
                        .classes("w-full h-full min-h-[400px]")
                        .props("readonly")
                    )


def _implant_tab(state: _BuilderState):
    with ui.column().classes("w-full gap-4 p-3"):
        ui.label("Template").classes("text-sm font-bold text-gray-200")

        template_options = {t.get("name", ""): t.get("display_name", t.get("name", "")) for t in state.templates}

        if template_options:
            ui.select(
                options=template_options,
                value=state.selected_template,
                label="Implant Template",
                on_change=lambda e: _on_template_change(state, e.value),
            ).props("outlined dense dark color=emerald options-dense").classes("w-full tech-select")

            for t in state.templates:
                if t.get("name") == state.selected_template:
                    with ui.row().classes("gap-2 items-center -mt-1"):
                        ui.badge(t.get("platform", ""), color="blue-grey-8").props("outline dense")
                        ui.badge(t.get("arch", ""), color="blue-grey-8").props("outline dense")
                        ui.badge(f"v{t.get('version', '')}", color="teal-8").props("outline dense")
                        ui.label(t.get("description", "")).classes("text-[11px] text-gray-500")
                    break
        else:
            ui.label("No templates found on server.").classes("text-amber-400 text-xs")

        ui.separator().classes("bg-white/5")

        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Modules").classes("text-sm font-bold text-gray-200")

            with ui.row().classes("items-center gap-1"):
                module_names = sorted([m["artifact_name"] for m in state.all_modules])

                if not module_names:

                    async def do_seed():
                        resp = await seed_modules()
                        if resp and resp.get("data"):
                            d = resp["data"]
                            notify(
                                f"Seeded: {d.get('created', 0)} new, {d.get('updated', 0)} updated",
                                type="positive",
                                color="emerald-9",
                            )
                        else:
                            notify("Seed failed", type="negative")

                    ui.button("SEED", on_click=do_seed).props("flat dense size=xs color=amber no-caps")
                else:

                    def show_add_module_popup():
                        available = [n for n in module_names if n not in state.selected_modules]
                        if not available:
                            notify("All modules already added", type="info")
                            return

                        with ui.dialog() as dlg, ui.card().classes("tech-dialog w-[400px] p-0 rounded overflow-hidden"):
                            with ui.row().classes(
                                "w-full bg-neutral-900/50 p-4 border-b border-white/5 " "items-center justify-between"
                            ):
                                ui.label("ADD MODULES").classes("tech-label-sub")
                                ui.button(icon="close", on_click=dlg.close).props("dense flat size=sm color=grey")

                            to_add = []
                            with ui.column().classes("p-4 gap-1 w-full max-h-[300px] overflow-auto"):
                                for mod_name in available:
                                    cb = ui.checkbox(mod_name, value=False).props("dense dark color=emerald")
                                    to_add.append((mod_name, cb))

                            with ui.row().classes("w-full bg-black/20 p-3 border-t border-white/5 justify-end gap-2"):
                                ui.button("CANCEL", on_click=dlg.close).props("flat dense color=grey no-caps")

                                def confirm_add():
                                    for name, cb in to_add:
                                        if cb.value and name not in state.selected_modules:
                                            state.selected_modules.append(name)
                                    dlg.close()
                                    _refresh_module_card(state)

                                ui.button("ADD", on_click=confirm_add).props("unelevated dense color=emerald no-caps")
                        dlg.open()

                    with (
                        ui.button(icon="add", on_click=show_add_module_popup)
                        .props("flat dense size=xs")
                        .classes("tech-btn-action-2")
                    ):
                        formatted_tooltip("Add Module")

        state.module_card = (
            ui.card()
            .classes("w-full min-h-[60px]")
            .style("border: 1px dashed #444; background: transparent; padding: 4px;")
        )
        _render_module_rows(state)

        if not state.selected_modules:
            with state.module_card, ui.column().classes("w-full items-center justify-center py-4 gap-1 opacity-40"):
                ui.icon("extension", size="md", color="neutral-600")
                ui.label("No modules selected").classes("tech-label-sub text-neutral-500 text-xs")


def _render_module_rows(state: _BuilderState):
    if not state.module_card:
        return

    for mod_name in list(state.selected_modules):
        with state.module_card, ui.row().classes(
            "w-full items-center gap-2 px-3 py-1.5 rounded "
            "hover:bg-white/5 transition-colors border-b border-white/5 last:border-0"
        ) as row:
            ui.label(mod_name).classes("flex-grow text-xs font-mono text-gray-300")

            async def view_source(name=mod_name):
                resp = await get_module_by_name(name)
                if resp and resp.get("data", {}).get("artifact_contents"):
                    try:
                        bundle = json.loads(resp["data"]["artifact_contents"])
                        source_parts = []
                        mod_info = bundle.get("module", {})
                        source_parts.append(
                            f"// Module: {mod_info.get('display_name', name)}\n"
                            f"// Category: {mod_info.get('category', 'unknown')}\n"
                            f"// {mod_info.get('description', '')}\n"
                        )
                        cmds = bundle.get("commands", {})
                        if cmds:
                            source_parts.append(f"// Commands: {', '.join(cmds.keys())}\n")
                        source_parts.append("")
                        for filename, content in bundle.get("files", {}).items():
                            source_parts.append(f"// ─── {filename} ───\n")
                            source_parts.append(content)
                            source_parts.append("\n")
                        _set_code_viewer(state, f"MODULE: {name}", "\n".join(source_parts))
                    except json.JSONDecodeError:
                        _set_code_viewer(state, f"MODULE: {name}", "// Error: invalid JSON")
                else:
                    _set_code_viewer(state, f"MODULE: {name}", "// Module not found in DB")

            is_required = mod_name in state.required_modules

            with ui.button(icon="visibility", on_click=view_source).props("flat dense size=xs color=grey"):
                formatted_tooltip("View Source")

            if is_required:
                with ui.icon("lock", size="xs", color="grey-7").classes("ml-1"):
                    formatted_tooltip("Required — cannot be removed")
            else:

                def remove_mod(name=mod_name, r=row):
                    if name in state.selected_modules:
                        state.selected_modules.remove(name)
                    r.delete()

                ui.button(icon="close", on_click=remove_mod).props("flat dense size=xs color=red")


def _refresh_module_card(state: _BuilderState):
    if state.module_card:
        state.module_card.clear()
        _render_module_rows(state)


def _loader_tab():
    with ui.column().classes("w-full h-full items-center justify-center gap-3 p-8 opacity-40"):
        ui.icon("help_outline", size="4rem", color="neutral-600")
        ui.label("LOADER CONFIGURATION").classes("text-sm font-bold text-gray-400")
        ui.label("BYOL (Bring Your Own Loader) support — coming soon.").classes("text-xs text-gray-500 text-center")


def _profiles_tab(state: _BuilderState):
    with ui.column().classes("w-full gap-4 p-3"):
        listener_options = {
            lis["listener_uuid"]: f"{lis.get('listener_name', 'unnamed')} "
            f"({lis.get('listener_type', '')} — "
            f"{lis.get('listener_host', '')}:{lis.get('listener_port', '')})"
            for lis in state.listeners
        }

        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Profiles").classes("text-sm font-bold text-gray-200")

            if listener_options:

                def show_add_listener_popup():
                    available = {k: v for k, v in listener_options.items() if k not in state.selected_listeners}
                    if not available:
                        notify("All listeners already added", type="info")
                        return

                    with ui.dialog() as dlg, ui.card().classes("tech-dialog w-[500px] p-0 rounded overflow-hidden"):
                        with ui.row().classes(
                            "w-full bg-neutral-900/50 p-4 border-b border-white/5 " "items-center justify-between"
                        ):
                            ui.label("ADD LISTENER PROFILES").classes("tech-label-sub")
                            ui.button(icon="close", on_click=dlg.close).props("dense flat size=sm color=grey")

                        to_add = []
                        with ui.column().classes("p-4 gap-1 w-full max-h-[300px] overflow-auto"):
                            for uuid, label in available.items():
                                cb = ui.checkbox(label, value=False).props("dense dark color=emerald")
                                to_add.append((uuid, cb))

                        with ui.row().classes("w-full bg-black/20 p-3 border-t border-white/5 justify-end gap-2"):
                            ui.button("CANCEL", on_click=dlg.close).props("flat dense color=grey no-caps")

                            def confirm():
                                for uuid, cb in to_add:
                                    if cb.value and uuid not in state.selected_listeners:
                                        state.selected_listeners.append(uuid)
                                dlg.close()
                                _refresh_listener_card(state)

                            ui.button("ADD", on_click=confirm).props("unelevated dense color=emerald no-caps")
                    dlg.open()

                with (
                    ui.button(icon="add", on_click=show_add_listener_popup)
                    .props("flat dense size=xs")
                    .classes("tech-btn-action-2")
                ):
                    formatted_tooltip("Add Listener Profile")

        if not listener_options:
            ui.label("No listeners found. Create listeners first.").classes("text-amber-400 text-xs")
            return

        state._listener_card = (
            ui.card()
            .classes("w-full min-h-[40px]")
            .style("border: 1px dashed #444; background: transparent; padding: 4px;")
        )
        _render_listener_rows(state, listener_options)

        if not state.selected_listeners:
            with state._listener_card, ui.column().classes("w-full items-center justify-center py-3 gap-1 opacity-40"):
                ui.icon("headphones", size="md", color="neutral-600")
                ui.label("No listeners added").classes("tech-label-sub text-neutral-500 text-xs")

        ui.separator().classes("bg-white/5")

        ui.label("Initial Beacon Channels").classes("text-sm font-bold text-gray-200")
        ui.label("Which listener's profile to use for the first GET and POST beacons.").classes("text-xs text-gray-500")

        ui.select(
            options=listener_options,
            value=state.init_get_listener,
            label="Initial GET Listener",
            on_change=lambda e: setattr(state, "init_get_listener", e.value),
        ).props("outlined dense dark color=emerald options-dense clearable").classes("w-full tech-select")

        ui.select(
            options=listener_options,
            value=state.init_post_listener,
            label="Initial POST Listener",
            on_change=lambda e: setattr(state, "init_post_listener", e.value),
        ).props("outlined dense dark color=emerald options-dense clearable").classes("w-full tech-select")

        ui.separator().classes("bg-white/5")

        ui.label("Callback Host").classes("text-sm font-bold text-gray-200")
        ui.label("IP or hostname the implant calls back to. Supports CDNs, redirectors, NAT.").classes(
            "text-xs text-gray-500"
        )

        ui.input(
            label="Callback Host",
            value=state.callback_host,
            placeholder="e.g. 10.0.0.5 or cdn.example.com",
            on_change=lambda e: setattr(state, "callback_host", e.value or ""),
        ).props("outlined dense dark color=emerald").classes("w-full tech-input")


def _render_listener_rows(state: _BuilderState, listener_options: dict):
    card = state._listener_card
    for uuid in list(state.selected_listeners):
        label = listener_options.get(uuid, uuid)
        with card, ui.row().classes(
            "w-full items-center gap-2 px-3 py-1.5 rounded "
            "hover:bg-white/5 transition-colors border-b border-white/5 last:border-0"
        ) as row:
            ui.label(label).classes("flex-grow text-xs font-mono text-gray-300")

            def remove_listener(u=uuid, r=row):
                if u in state.selected_listeners:
                    state.selected_listeners.remove(u)
                r.delete()

            ui.button(icon="close", on_click=remove_listener).props("flat dense size=xs color=red")


def _refresh_listener_card(state: _BuilderState):
    if hasattr(state, "_listener_card") and state._listener_card:
        listener_options = {
            lis["listener_uuid"]: f"{lis.get('listener_name', 'unnamed')} "
            f"({lis.get('listener_type', '')} — "
            f"{lis.get('listener_host', '')}:{lis.get('listener_port', '')})"
            for lis in state.listeners
        }
        state._listener_card.clear()
        _render_listener_rows(state, listener_options)


def _misc_tab(state: _BuilderState):
    with ui.column().classes("w-full gap-4 p-3"):
        ui.label("Executable Name").classes("text-sm font-bold text-gray-200")
        ui.input(
            label="Implant Name",
            value=state.implant_name,
            placeholder="e.g. op_alpha",
            on_change=lambda e: setattr(state, "implant_name", e.value or ""),
        ).props("outlined dense dark color=emerald").classes("w-full tech-input")

        ui.separator().classes("bg-white/5")

        ui.label("Build Options").classes("text-sm font-bold text-gray-200")

        ui.switch(
            "Debug Logging",
            value=state.debug_enabled,
            on_change=lambda e: setattr(state, "debug_enabled", e.value),
        ).classes("tech-switch")
        ui.label("Enables IMPLANT_DEBUG_LOGS. Do not use in production.").classes("text-[11px] text-gray-500 -mt-2")

        ui.switch(
            "Clear Build Cache",
            value=state.clear_cache,
            on_change=lambda e: setattr(state, "clear_cache", e.value),
        ).classes("tech-switch")
        ui.label("Forces full recompilation.").classes("text-[11px] text-gray-500 -mt-2")

        ui.separator().classes("bg-white/5")

        ui.label("Save / Load Config").classes("text-sm font-bold text-gray-200")

        with ui.row().classes("gap-2 w-full"):
            config_name_input = (
                ui.input(
                    label="Config Name",
                    placeholder="e.g. default_win64",
                )
                .props("outlined dense dark color=emerald")
                .classes("flex-grow tech-input")
            )

            async def do_save_config():
                name = (config_name_input.value or "").strip()
                if not name:
                    notify("Enter a config name", type="warning", color="orange-9")
                    return
                config_data = _build_config_json(state)
                resp = await save_build_config(name, config_data)
                if resp:
                    notify(f"Config '{name}' saved", type="positive", color="emerald-9")
                else:
                    notify("Save failed", type="negative")

            ui.button("SAVE", icon="save", on_click=do_save_config).props(
                "unelevated dense color=emerald no-caps size=sm"
            )

        def show_summary():
            summary = _build_config_json(state)
            _set_code_viewer(state, "BUILD_CONFIG", json.dumps(json.loads(summary), indent=2))

        ui.button("VIEW CONFIG JSON", icon="preview", on_click=show_summary).props(
            "flat dense no-caps size=sm"
        ).classes("tech-btn-secondary")


def _on_template_change(state: _BuilderState, value: str):
    state.selected_template = value
    for t in state.templates:
        if t.get("name") == value:
            state.default_modules = t.get("build", {}).get("default_modules", [])
            state.selected_modules = list(state.default_modules)
            _refresh_module_card(state)
            break


def _set_code_viewer(state: _BuilderState, title: str, content: str):
    if state.code_title_label:
        state.code_title_label.set_text(f"{title} //")
    if state.code_viewer:
        state.code_viewer.value = content


def _build_config_json(state: _BuilderState) -> str:
    return json.dumps(
        {
            "template_name": state.selected_template,
            "modules": state.selected_modules,
            "implant_name": state.implant_name,
            "callback_host": state.callback_host,
            "listeners": state.selected_listeners,
            "init_get_listener": state.init_get_listener,
            "init_post_listener": state.init_post_listener,
            "debug": state.debug_enabled,
            "clear_cache": state.clear_cache,
        }
    )


def _apply_config(state: _BuilderState, config_contents: str):
    try:
        data = json.loads(config_contents)
        state.selected_template = data.get("template_name", state.selected_template)
        state.selected_modules = data.get("modules", state.selected_modules)
        state.implant_name = data.get("implant_name", "")
        state.callback_host = data.get("callback_host", "")
        state.selected_listeners = data.get("listeners", [])
        state.init_get_listener = data.get("init_get_listener")
        state.init_post_listener = data.get("init_post_listener")
        state.debug_enabled = data.get("debug", False)
        state.clear_cache = data.get("clear_cache", False)
    except json.JSONDecodeError:
        notify("Invalid config JSON", type="negative")
