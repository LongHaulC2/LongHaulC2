from nicegui import app, ui


@ui.page("/login")
def login_page():
    # Clear default padding to allow full-screen centering
    ui.context.client.content.classes("h-full p-0 gap-0")

    # set bg image
    ui.element("div").classes("fixed inset-0 -z-10 bg-[url('/static/world.png')] bg-cover bg-center")
    # Main Container (Centers the card vertically & horizontally)
    with ui.column().classes("w-full h-screen items-center justify-center"):  # noqa: SIM117
        # The Login Card
        with ui.card().classes("w-[400px] max-w-[90vw] p-0 gap-0 tech-glass-panel"):
            # Slightly lighter background to differentiate header
            with ui.column().classes("w-full items-center p-8 pb-6 border-b border-white/5 bg-white/5"):
                # world icon
                ui.image("/static/world_outline.png").classes(
                    "p-3 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-3 size-20"
                )
                # Title
                ui.label("LONGHAULC2").classes("tech-label-sub")

            # inputs
            with ui.column().classes("w-full p-8 gap-5"):
                host = (  # noqa: F841, not used yet, but will when login is fully implemented
                    ui.input("SERVER_ADDRESS")
                    .props("outlined dense dark color=emerald autofocus")
                    .classes("w-full font-mono")
                    .on("keydown.enter", lambda: password.run_method("focus"))
                )
                with host:
                    ui.tooltip("Server address and port of LongHaulC2 Server. Ex: `10.0.0.50:45045`")
                # Username
                username = (  # noqa: F841, not used yet, but will when login is fully implemented
                    ui.input("USERNAME")
                    .props("outlined dense dark color=emerald autofocus")
                    .classes("w-full font-mono")
                    .on("keydown.enter", lambda: password.run_method("focus"))
                )

                # Password
                password = (
                    ui.input("PASSWORD", password=True, password_toggle_button=True)
                    .props("outlined dense dark color=emerald")
                    .classes("w-full font-mono")
                    .on(
                        "keydown.enter",
                        lambda: ui.notify("AUTHENTICATING...", type="ongoing", color="emerald-9"),
                    )
                )

                # Spacer
                ui.element("div").classes("h-1")

                # Login Button
                # Reuse 'tech-btn-action' for the hover glow effect
                with (
                    ui.button(
                        on_click=lambda: handle_login(host=host.value, user=username.value, password=password.value),
                        color="emerald-9",
                    )
                    .classes("w-full tech-btn-action py-2")
                    .props("unelevated dense")
                ):
                    ui.label("LOGIN").classes("tech-label-sub")
                    ui.icon("arrow_forward", size="xs").classes("ml-2")

            # Footer
            with ui.row().classes("w-full p-3 bg-black/20 border-t border-white/5 justify-between items-center px-6"):
                ...

    def handle_login(host, user, password):  # noqa: ARG001 - going to be filled in when login logic is done
        if host:
            # Save the host directly to the user's session
            app.storage.user["api_host"] = host
            ui.notify(f"Connected to {host}", type="positive")
            ui.navigate.to("/operations")
        else:
            ui.notify("Please enter a valid server address", type="warning")
