import logging

from nicegui import app, ui

from client.modules.api_calls import (
    change_password,
    delete_own_account,
    delete_user,
    disable_totp,
    get_all_users,
    get_current_user,
    register_user,
    setup_totp,
    verify_totp,
)
from client.pages.menu import setup_menu
from client.utils.helpers import notify

server_log = logging.getLogger("server")


def initialize_default_settings() -> None:
    defaults = {
        "auto_refresh_rate": 1,
        "notification_position": "bottom",
    }
    for key, value in defaults.items():
        if key not in app.storage.user:
            app.storage.user[key] = value


@ui.page("/settings")
async def settings_page() -> None:
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Settings")
    initialize_default_settings()
    await settings_tabbed_view()


@ui.page("/settings/{tab}")
async def settings_page_with_tab(tab: str) -> None:
    ui.context.client.content.classes("h-full p-0 gap-0")
    ui.context.client.page_container.default_slot.children[0].props(
        ':style-fn="o => ({ height: `calc(100vh - ${o}px)` })"'
    )

    setup_menu("Settings")
    initialize_default_settings()
    await settings_tabbed_view(initial_tab=tab)


async def settings_tabbed_view(initial_tab: str = "preferences") -> None:
    with ui.column().classes("w-full h-full gap-0 tech-glass-panel bg-[#0a0a0a]"):
        # Header
        with (
            ui.row().classes(
                "w-full items-center justify-between tech-header-bar p-4 border-b border-white/5 bg-[#0f0f0f]"
            ),
            ui.row().classes("items-center gap-3"),
        ):
            ui.icon("tune", color="emerald-500").classes("text-xl")
            ui.label("SETTINGS //").classes("tech-label-sub")

        # Tabs
        tab_style = "font-mono text-xs tracking-widest"
        with ui.tabs().props("dense active-color=emerald indicator-color=emerald").classes(
            "w-full bg-[#0f0f0f] border-b border-white/5"
        ) as tabs:
            ui.tab("preferences", label="PREFERENCES", icon="memory").classes(tab_style)
            ui.tab("profile", label="PROFILE", icon="person").classes(tab_style)
            ui.tab("users", label="USERS", icon="group").classes(tab_style)

        tabs.set_value(initial_tab)

        with ui.tab_panels(tabs, value=initial_tab).props("animated").classes("w-full flex-grow bg-transparent"):
            with ui.tab_panel("preferences").classes("p-0"):
                await _build_preferences_tab()

            with ui.tab_panel("profile").classes("p-0"):
                await _build_profile_tab()

            with ui.tab_panel("users").classes("p-0"):
                await _build_users_tab()


# ---------------------------------------------------------------------------
# Tab: Preferences
# ---------------------------------------------------------------------------
async def _build_preferences_tab() -> None:
    with ui.scroll_area().classes("w-full h-full p-8"):  # noqa: SIM117
        with ui.column().classes("w-full max-w-4xl mx-auto gap-8 pb-20"):
            ui.label("All values here auto-save on change").classes("tech-header-bar w-full text-center")

            with ui.column().classes("w-full gap-4 mt-4"):
                with ui.row().classes("w-full items-center gap-2 border-b border-white/10 pb-2"):
                    ui.icon("memory", color="neutral-500").classes("text-sm")
                    ui.label("Settings").classes("tech-label-sub")

                with ui.row().classes("w-full gap-8 items-start bg-white/5 p-4 rounded border border-white/5"):
                    with ui.column().classes("w-1/3 gap-1"):
                        ui.label("Element Auto Refresh Rate").classes("tech-label-header-section underline font-bold")
                        ui.number(value=1, min=1, step=1, format="%.0f").bind_value(
                            app.storage.user, "auto_refresh_rate"
                        ).props("outlined dense dark color=emerald").classes("tech-label-sub w-32 my-1")
                        ui.label("Lower values increase server load but provide more frequent updates.").classes(
                            "tech-label-sub opacity-70"
                        )

                    with ui.column().classes("flex-grow gap-1 border-l border-white/10 pl-6"):
                        ui.label("Affects").classes("tech-label-sub font-bold mb-1")
                        ui.separator()
                        with ui.column().classes("gap-2 pl-2"):
                            for component in [
                                "Operations: Terminal update interval",
                                "Operations: Implant Table update interval",
                                "Footer: Update interval",
                                "Graph: Update interval",
                            ]:
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon("circle", size="6px", color="emerald")
                                    ui.label(component).classes("tech-label-sub")

                with (  # noqa: SIM117
                    ui.row().classes("w-full gap-8 items-start bg-white/5 p-4 rounded border border-white/5"),
                    ui.column().classes("w-1/3 gap-1"),
                ):
                    ui.label("Notification Position").classes("tech-label-header-section underline font-bold")
                    ui.select(
                        options=[
                            "top-left",
                            "top-right",
                            "top",
                            "bottom-left",
                            "bottom-right",
                            "bottom",
                            "left",
                            "right",
                            "center",
                        ],
                        value="bottom",
                    ).bind_value(app.storage.user, "notification_position").props(
                        "outlined dense dark color=emerald"
                    ).classes("tech-label-sub w-40 my-1")
                    ui.label("Where notifications appear on screen.").classes("tech-label-sub opacity-70")

            # Danger zone
            with ui.column().classes("w-full gap-4 mt-8"):
                with ui.row().classes("w-full items-center gap-2 border-b border-red-500/20 pb-2"):
                    ui.icon("warning", color="red-500").classes("text-sm")
                    ui.label("WARNING").classes("text-xs font-mono text-red-500 tracking-widest font-bold uppercase")

                with ui.row().classes(
                    "w-full justify-between items-center bg-red-900/10 p-4 rounded " "border border-red-500/20"
                ):
                    with ui.column().classes("gap-0"):
                        ui.label("RESET SETTINGS").classes("tech-label-header-section underline")
                        ui.label("Revert all settings to system defaults. This action cannot be undone.").classes(
                            "tech-label-sub"
                        )
                        ui.label(
                            "You will be logged out, as this clears all user settings, " "including your active token"
                        ).classes("tech-label-sub")

                    def trigger_reset() -> None:
                        app.storage.user.clear()
                        initialize_default_settings()
                        notify(
                            "PREFERENCES RESET TO DEFAULT",
                            type="warning",
                            color="red-9",
                        )
                        ui.navigate.to("/settings")

                    ui.button("RESET TO DEFAULT", on_click=trigger_reset).props("outline dense color=red").classes(
                        "font-mono text-xs font-bold tracking-wider"
                    )


# ---------------------------------------------------------------------------
# Tab: Profile
# ---------------------------------------------------------------------------
async def _build_profile_tab() -> None:
    username = app.storage.user.get("username", "unknown")
    user_data = await get_current_user()
    has_totp = False
    if user_data and user_data.get("data"):
        has_totp = user_data["data"].get("has_totp", False)

    with ui.scroll_area().classes("w-full h-full p-8"):  # noqa: SIM117
        with ui.column().classes("w-full max-w-4xl mx-auto gap-8 pb-20"):
            # Account info
            with ui.column().classes("w-full gap-4"):
                with ui.row().classes("w-full items-center gap-2 border-b border-white/10 pb-2"):
                    ui.icon("badge", color="neutral-500").classes("text-sm")
                    ui.label("Account Info").classes("tech-label-sub")

                with ui.row().classes("w-full gap-8 items-center bg-white/5 p-4 rounded border border-white/5"):
                    with ui.column().classes("gap-1"):
                        ui.label("USERNAME").classes("tech-label-sub opacity-70")
                        ui.label(username).classes("tech-label-header-bold text-emerald-400")
                    with ui.column().classes("gap-1 ml-12"):
                        ui.label("2FA STATUS").classes("tech-label-sub opacity-70")
                        if has_totp:
                            ui.label("ENABLED").classes("tech-label-header-bold text-emerald-400")
                        else:
                            ui.label("DISABLED").classes("tech-label-header-bold text-red-400")

            # Change password
            with ui.column().classes("w-full gap-4 mt-4"):
                with ui.row().classes("w-full items-center gap-2 border-b border-white/10 pb-2"):
                    ui.icon("lock", color="neutral-500").classes("text-sm")
                    ui.label("Change Password").classes("tech-label-sub")

                input_props = "outlined dense dark color=emerald input-class='font-mono text-sm'"

                with ui.column().classes("w-full bg-white/5 p-4 rounded border border-white/5 gap-4"):
                    old_pw = (
                        ui.input("Current Password", password=True, password_toggle_button=True)
                        .props(input_props)
                        .classes("w-full")
                    )

                    with ui.row().classes("w-full gap-4"):
                        new_pw = (
                            ui.input("New Password", password=True, password_toggle_button=True)
                            .props(input_props)
                            .classes("flex-1")
                        )

                        confirm_pw = (
                            ui.input(
                                "Confirm New Password",
                                password=True,
                                password_toggle_button=True,
                            )
                            .props(input_props)
                            .classes("flex-1")
                        )

                    async def handle_change_password():
                        if not old_pw.value or not new_pw.value:
                            notify("Fill in all password fields", type="warning")
                            return
                        if new_pw.value != confirm_pw.value:
                            notify("New passwords do not match", type="negative")
                            return
                        result = await change_password(old_pw.value, new_pw.value)
                        if result and result.get("status") == "200":
                            notify("Password changed successfully", type="positive")
                            old_pw.value = ""
                            new_pw.value = ""
                            confirm_pw.value = ""
                        else:
                            notify(
                                "Failed to change password — check current password",
                                type="negative",
                            )

                    with ui.row().classes("w-full justify-end"):
                        ui.button("CHANGE PASSWORD", on_click=handle_change_password).props(
                            "unelevated dense color=emerald"
                        ).classes("font-mono text-xs font-bold tracking-wider")

            # TOTP 2FA
            with ui.column().classes("w-full gap-4 mt-4"):
                with ui.row().classes("w-full items-center gap-2 border-b border-white/10 pb-2"):
                    ui.icon("security", color="neutral-500").classes("text-sm")
                    ui.label("Two-Factor Authentication (TOTP)").classes("tech-label-sub")

                totp_container = ui.column().classes("w-full bg-white/5 p-4 rounded border border-white/5 gap-4")
                with totp_container:
                    if has_totp:
                        ui.label("TOTP is currently enabled on this account.").classes(
                            "tech-label-sub text-emerald-400"
                        )

                        async def handle_disable_totp():
                            result = await disable_totp()
                            if result and result.get("status") == "200":
                                notify("TOTP disabled", type="positive")
                                ui.navigate.to("/settings/profile")
                            else:
                                notify("Failed to disable TOTP", type="negative")

                        ui.button("DISABLE 2FA", on_click=handle_disable_totp).props("outline dense color=red").classes(
                            "font-mono text-xs font-bold tracking-wider"
                        )
                    else:
                        ui.label("TOTP is not enabled. Set up an authenticator app.").classes(
                            "tech-label-sub opacity-70"
                        )

                        async def handle_setup_totp():
                            result = await setup_totp()
                            if not result or result.get("status") != "200":
                                notify(
                                    "Failed to generate TOTP secret",
                                    type="negative",
                                )
                                return
                            data = result.get("data", {})
                            secret = data.get("secret", "")
                            qr_code = data.get("qr_code", "")

                            totp_container.clear()
                            with totp_container:
                                ui.label("Scan this QR code with your authenticator app:").classes("tech-label-sub")
                                if qr_code:
                                    ui.image(qr_code).classes("w-48 h-48 rounded border border-white/10")
                                ui.label("Or enter the secret manually:").classes("tech-label-sub mt-2")
                                ui.label(secret).classes(
                                    "font-mono text-sm text-amber-400 " "bg-black/40 p-2 rounded select-all"
                                )
                                ui.label("Enter a code from your app to verify:").classes("tech-label-sub mt-4")
                                code_input = (
                                    ui.input("6-digit code")
                                    .props("outlined dense dark color=emerald " "input-class='font-mono text-sm'")
                                    .classes("w-48")
                                )

                                async def handle_verify():
                                    vresult = await verify_totp(code_input.value)
                                    if vresult and vresult.get("status") == "200":
                                        notify(
                                            "TOTP verified and enabled!",
                                            type="positive",
                                        )
                                        ui.navigate.to("/settings/profile")
                                    else:
                                        notify(
                                            "Invalid code — try again",
                                            type="negative",
                                        )

                                ui.button("VERIFY & ENABLE", on_click=handle_verify).props(
                                    "unelevated dense color=emerald"
                                ).classes("font-mono text-xs font-bold tracking-wider")

                        ui.button("SETUP 2FA", on_click=handle_setup_totp).props(
                            "unelevated dense color=emerald"
                        ).classes("font-mono text-xs font-bold tracking-wider")

            # Danger zone
            with ui.column().classes("w-full gap-4 mt-8"):
                with ui.row().classes("w-full items-center gap-2 border-b border-red-500/20 pb-2"):
                    ui.icon("warning", color="red-500").classes("text-sm")
                    ui.label("DANGER ZONE").classes(
                        "text-xs font-mono text-red-500 tracking-widest " "font-bold uppercase"
                    )

                with ui.row().classes(
                    "w-full justify-between items-center bg-red-900/10 p-4 " "rounded border border-red-500/20"
                ):
                    with ui.column().classes("gap-0"):
                        ui.label("DELETE ACCOUNT").classes("tech-label-header-section underline")
                        ui.label("Permanently delete your operator account. " "This cannot be undone.").classes(
                            "tech-label-sub"
                        )

                    async def handle_delete_account():
                        result = await delete_own_account()
                        if result and result.get("status") == "200":
                            notify("Account deleted", type="positive")
                            app.storage.user.clear()
                            ui.navigate.to("/login")
                        else:
                            notify("Failed to delete account", type="negative")

                    with ui.dialog() as confirm_dialog, ui.card().classes("bg-[#0a0a0a] border border-red-500/30"):
                        ui.label("Are you sure? This will permanently delete your account.").classes(
                            "text-sm font-mono text-neutral-300"
                        )
                        with ui.row().classes("w-full justify-end gap-3 mt-4"):
                            ui.button(
                                "DELETE",
                                on_click=lambda: (
                                    confirm_dialog.close(),
                                    handle_delete_account(),
                                ),
                            ).props("unelevated dense color=red").classes("font-mono text-xs font-bold")
                            ui.button("CANCEL", on_click=confirm_dialog.close).props(
                                "outline dense color=grey"
                            ).classes("font-mono text-xs")

                    ui.button("DELETE MY ACCOUNT", on_click=confirm_dialog.open).props(
                        "outline dense color=red"
                    ).classes("font-mono text-xs font-bold tracking-wider")


# ---------------------------------------------------------------------------
# Tab: Users
# ---------------------------------------------------------------------------
async def _build_users_tab() -> None:
    selected_rows = []
    user_table = None

    with ui.scroll_area().classes("w-full h-full p-8"):  # noqa: SIM117
        with ui.column().classes("w-full max-w-4xl mx-auto gap-8 pb-20"):
            # Add New User
            with ui.column().classes("w-full gap-4"):
                with ui.row().classes("w-full items-center gap-2 border-b border-white/10 pb-2"):
                    ui.icon("person_add", color="neutral-500").classes("text-sm")
                    ui.label("Add New User").classes("tech-label-sub")

                input_props = "outlined dense dark color=emerald input-class='font-mono text-sm'"

                with ui.column().classes("w-full bg-white/5 p-4 rounded border border-white/5 gap-4"):
                    new_username = ui.input("Username").props(input_props).classes("w-full")

                    with ui.row().classes("w-full gap-4"):
                        new_password = (
                            ui.input("Password", password=True, password_toggle_button=True)
                            .props(input_props)
                            .classes("flex-1")
                        )

                        confirm_password = (
                            ui.input(
                                "Confirm Password",
                                password=True,
                                password_toggle_button=True,
                            )
                            .props(input_props)
                            .classes("flex-1")
                        )

                    async def handle_create_user():
                        if not new_username.value or not new_password.value:
                            notify("Username and password are required", type="warning")
                            return
                        if new_password.value != confirm_password.value:
                            notify("Passwords do not match", type="negative")
                            return

                        result = await register_user(new_username.value.strip(), new_password.value)
                        if result and result.get("status") == "200":
                            notify(f"User '{new_username.value}' created", type="positive")
                            new_username.value = ""
                            new_password.value = ""
                            confirm_password.value = ""
                            await refresh_user_list()
                        else:
                            msg = result.get("message", "Failed to create user") if result else "Failed to create user"
                            notify(msg, type="negative")

                    with ui.row().classes("w-full justify-end"):
                        ui.button("CREATE USER", on_click=handle_create_user).props(
                            "unelevated dense color=emerald"
                        ).classes("font-mono text-xs font-bold tracking-wider")

            # Current Users
            with ui.column().classes("w-full gap-4 mt-4"):
                with ui.row().classes("w-full items-center justify-between border-b border-white/10 pb-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("people", color="neutral-500").classes("text-sm")
                        ui.label("Current Users").classes("tech-label-sub")

                    async def handle_delete_selected():
                        if not selected_rows:
                            notify("No users selected", type="warning")
                            return
                        names = [r["username"] for r in selected_rows if r["username"].lower() != "longhaul"]
                        if not names:
                            notify("Cannot delete the default account", type="warning")
                            return
                        for name in names:
                            result = await delete_user(name)
                            if result and result.get("status") == "200":
                                notify(f"User '{name}' deleted", type="positive")
                            else:
                                notify(f"Failed to delete '{name}'", type="negative")
                        await refresh_user_list()

                    delete_btn = (
                        ui.button("DELETE SELECTED", icon="delete", on_click=handle_delete_selected)
                        .props("outline dense color=red")
                        .classes("font-mono text-xs font-bold tracking-wider")
                    )
                    delete_btn.set_visibility(False)

                columns = [
                    {"name": "username", "label": "USERNAME", "field": "username", "align": "left", "sortable": True},
                    {"name": "has_totp", "label": "2FA", "field": "has_totp", "align": "center", "sortable": True},
                    {"name": "badge", "label": "", "field": "badge", "align": "left", "sortable": False},
                ]

                user_table = (
                    ui.table(
                        columns=columns,
                        rows=[],
                        row_key="username",
                        selection="multiple",
                    )
                    .props(
                        "flat bordered dark dense separator=cell"
                        " color=emerald"
                        " table-header-class='bg-[#111] text-emerald-500 font-mono text-xs tracking-widest'"
                    )
                    .classes("w-full user-table")
                )

                user_table.on_select(lambda e: _on_selection_change(e, selected_rows, delete_btn))

                user_table.add_slot(
                    "body-cell-has_totp",
                    r"""
                    <q-td :props="props">
                        <q-icon
                            :name="props.row.has_totp ? 'verified_user' : 'shield'"
                            :color="props.row.has_totp ? 'green' : 'grey-7'"
                            size="xs"
                        />
                        <span
                            class="font-mono text-xs ml-1"
                            :class="props.row.has_totp ? 'text-green-400' : 'text-neutral-500'"
                        >
                            {{ props.row.has_totp ? 'ENABLED' : 'OFF' }}
                        </span>
                    </q-td>
                    """,
                )

                user_table.add_slot(
                    "body-cell-badge",
                    r"""
                    <q-td :props="props">
                        <q-badge
                            v-if="props.row.username.toLowerCase() === 'longhaul'"
                            color="amber-9"
                            text-color="white"
                            label="DEFAULT"
                            class="font-mono text-[10px]"
                        />
                    </q-td>
                    """,
                )

    async def refresh_user_list():
        nonlocal selected_rows
        selected_rows.clear()
        delete_btn.set_visibility(False)
        result = await get_all_users()
        rows = []
        if result and result.get("data"):
            rows = result["data"]
        user_table.rows = rows
        user_table.selected = []
        user_table.update()

    await refresh_user_list()


def _on_selection_change(e, selected_rows, delete_btn):
    selected_rows.clear()
    selected_rows.extend(e.selection)
    has_deletable = any(r["username"].lower() != "longhaul" for r in selected_rows)
    delete_btn.set_visibility(len(selected_rows) > 0 and has_deletable)
