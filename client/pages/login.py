import re

from nicegui import app, ui

from client.info import LOGIN_BANNER
from client.modules.api_calls import authenticate_to_server
from client.pages.formatted_tooltip import formatted_tooltip


def _validate_server_address(v: str) -> str | None:
    """Returns an error string if invalid, None if valid."""
    if not v:
        return None
    if not v.lower().startswith(("http://", "https://")):
        return 'Requires an "http://" or "https://" prefix'
    stripped = re.sub(r"^https?://", "", v, flags=re.IGNORECASE)
    if not stripped or stripped.startswith(":"):
        return "Must include a host (URL or IP address)"
    if not re.search(r":\d+$", stripped):
        return "Must include a port number (e.g. :45045)"
    return None


@ui.page("/login")
def login_page():
    # Clear default padding to allow full-screen centering
    ui.context.client.content.classes("h-full p-0 gap-0")

    # Set bg image with a dark overlay to ensure the glass card pops
    ui.element("div").classes("fixed inset-0 -z-10 bg-[url('/static/world.png')] bg-cover bg-center")
    ui.element("div").classes("fixed inset-0 -z-10 bg-black/60")  # Darkens the background image

    # Main Container (Centers the card vertically & horizontally)
    with ui.column().classes("w-full h-screen items-center justify-center"):  # noqa
        # The Login Card
        with ui.card().classes(
            "w-[450px] max-w-[90vw] p-0 gap-0 bg-[#0a0a0a]/90 backdrop-blur-md border border-white/10 shadow-2xl overflow-hidden"  # noqa - style
        ):
            # --- HEADER ---
            with ui.column().classes("w-full items-center p-8 pb-6 border-b border-white/5 bg-white/5 relative"):
                # Accent bar at the top
                ui.element("div").classes("absolute top-0 left-0 w-full h-1 bg-emerald-500")

                # World icon
                ui.image("/static/world_outline.png").classes(
                    "p-3 rounded-full bg-emerald-500/10 border border-emerald-500/30 mb-3 w-16 h-16"
                )

                # Title
                ui.label("LONGHAUL C2").classes("text-xl font-black tracking-[0.3em] text-white font-mono uppercase")

            # --- INPUTS ---
            with ui.column().classes("w-full p-8 gap-5"):
                # Host
                host = (
                    ui.input(
                        "SERVER_ADDRESS",
                        placeholder="https://10.0.0.50:45045",
                        validation=_validate_server_address,
                    )
                    .props(
                        "outlined dense dark color=emerald autofocus hide-bottom-space input-class='font-mono text-sm'"
                    )
                    .classes("w-full")
                    .on("keydown.enter", lambda: username.run_method("focus"))  # Fixed flow
                )
                with host:
                    formatted_tooltip(
                        title="Target LongHaulC2 Server Address",
                        body="Format: https://<host>:<port>  e.g. https://10.0.0.50:45045",
                    )

                # Username
                username = (
                    ui.input("USERNAME")
                    .props("outlined dense dark color=emerald input-class='font-mono text-sm'")
                    .classes("w-full")
                    .on("keydown.enter", lambda: password.run_method("focus"))
                )

                # Password
                password = (
                    ui.input("PASSWORD", password=True, password_toggle_button=True)
                    .props("outlined dense dark color=emerald input-class='font-mono text-sm'")
                    .classes("w-full")
                    .on(
                        "keydown.enter",
                        lambda: handle_login(host_value=host.value, user=username.value, password=password.value),
                    )
                )

                ui.element("div").classes("h-1")  # Spacer

                # Login Button
                with (
                    ui.button(
                        on_click=lambda: handle_login(
                            host_value=host.value, user=username.value, password=password.value
                        ),
                    )
                    .classes(
                        "w-full py-2 bg-emerald-900/50 hover:bg-emerald-600/80 border border-emerald-500/50 transition-all duration-300"  # noqa - styling
                    )
                    .props("unelevated dense")
                ):
                    ui.label("LOGIN").classes("text-xs font-mono font-bold tracking-[0.2em] text-white")
                    ui.icon("login", size="xs").classes("ml-2 text-white")

            # --- FOOTER / BANNER ---
            with ui.column().classes("w-full bg-[#050505] border-t border-white/5 p-4 gap-0"):  # noqa
                # Scrollable Banner Area
                with ui.scroll_area().classes("h-24 w-full pr-3 custom-scrollbar"):
                    ui.label(LOGIN_BANNER.strip()).classes(
                        "text-[12px] font-mono text-neutral-500 tracking-wide leading-relaxed whitespace-pre-line"
                    )

    async def handle_login(host_value, user, password):
        if not host_value:
            ui.notify("Please enter a server address", type="warning")
            return

        error = _validate_server_address(host_value)
        if error:
            host.validate()  # trigger inline display of the error
            ui.notify(error, type="warning")
            return

        app.storage.user["api_host"] = host_value

        tokens = await authenticate_to_server(username=user, password=password)

        if not tokens:
            ui.notify(f"Authentication to {host_value} failed", type="negative")
            return

        refresh_token = tokens.get("data", {}).get("refresh_token")
        access_token = tokens.get("data", {}).get("access_token")

        if refresh_token and access_token:
            app.storage.user["refresh_token"] = refresh_token
            app.storage.user["access_token"] = access_token

            ui.notify(f"Connected to {host_value}", type="positive")
            ui.navigate.to("/operations")
            return

        ui.notify(f"Authentication to {host_value} failed", type="negative")
