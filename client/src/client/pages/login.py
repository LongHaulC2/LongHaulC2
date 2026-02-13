from nicegui import ui


@ui.page("/login")
def login_page():
    # Clear default padding to allow full-screen centering
    ui.context.client.content.classes("h-full p-0 gap-0")

    # set bg image
    ui.element("div").classes(
        "fixed inset-0 -z-10 bg-[url('/static/world.png')] bg-cover bg-center"
    )
    # Main Container (Centers the card vertically & horizontally)
    with ui.column().classes("w-full h-full items-center justify-center"):

        # The Login Card
        # We reuse 'tech-glass-panel' from your global CSS for the frosted look & border
        with ui.card().classes("w-[400px] max-w-[90vw] p-0 gap-0 tech-glass-panel"):

            # --- HEADER ---
            # Slightly lighter background to differentiate header
            with ui.column().classes(
                "w-full items-center p-8 pb-6 border-b border-white/5 bg-white/5"
            ):

                # Biometric Icon with subtle ring
                with ui.element("div").classes(
                    "p-3 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-3"
                ):
                    ui.icon("fingerprint", size="2em", color="emerald-500")

                # Title
                ui.label("SYSTEM_ACCESS").classes(
                    "text-lg font-bold tracking-widest text-emerald-500 font-mono"
                )
                ui.label("RESTRICTED AREA // AUTH REQ").classes(
                    "text-[10px] text-neutral-500 font-mono mt-1"
                )

            # --- INPUT AREA ---
            with ui.column().classes("w-full p-8 gap-5"):

                # Username
                username = (
                    ui.input("OPERATOR_ID")
                    .props("outlined dense dark color=emerald autofocus")
                    .classes("w-full font-mono")
                    .on("keydown.enter", lambda: password.run_method("focus"))
                )

                # Password
                password = (
                    ui.input("ACCESS_KEY", password=True, password_toggle_button=True)
                    .props("outlined dense dark color=emerald")
                    .classes("w-full font-mono")
                    .on(
                        "keydown.enter",
                        lambda: ui.notify(
                            "AUTHENTICATING...", type="ongoing", color="emerald-9"
                        ),
                    )
                )

                # Spacer
                ui.element("div").classes("h-1")

                # Login Button
                # Reuse 'tech-btn-action' for the hover glow effect
                with ui.button(on_click=lambda: ui.open("/operations")).classes(
                    "w-full tech-btn-action py-2"
                ).props("unelevated dense"):

                    ui.label("INITIATE SESSION").classes(
                        "font-bold tracking-widest text-xs"
                    )
                    ui.icon("arrow_forward", size="xs").classes("ml-2")

            # --- STATUS FOOTER ---
            with ui.row().classes(
                "w-full p-3 bg-black/20 border-t border-white/5 justify-between items-center px-6"
            ):

                # Blinking Status Light
                with ui.row().classes("items-center gap-2"):
                    ui.element("div").classes(
                        "w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"
                    )
                    ui.label("GATEWAY_ONLINE").classes(
                        "text-[10px] font-mono text-emerald-500/50"
                    )

                ui.label("SECURE_CONNECTION").classes(
                    "text-[10px] font-mono text-neutral-600"
                )
