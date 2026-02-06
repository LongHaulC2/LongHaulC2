import asyncio

from nicegui import ui

from client.src.client.style import *

from ..utils.checks import check_type


def setup_menu(title: str):
    check_type(title, str, "title")

    # 1. Drawer Setup
    # width=280: Standard width for tech consoles
    # behavior='mobile': Forces it to overlay content (smoother for this style)
    left_drawer = (
        ui.left_drawer(value=False, elevated=False, bordered=False)
        .props("width=280 behavior=mobile")
        .classes("bg-[#0F0F0F]")
    )

    # 2. Header (Glassmorphism)
    with ui.header().classes(
        "bg-black/40 backdrop-blur-md border-b border-white/5 h-16 row items-center px-4"
    ) as header:

        # Toggle Button
        ui.button(on_click=lambda: left_drawer.toggle(), icon="menu").props(
            "flat dense round color=white"
        ).classes("opacity-70 hover:opacity-100 transition-opacity")

        # Page Title
        with ui.row().classes("items-center gap-2 ml-4"):
            ui.element("div").classes("w-1 h-4 bg-emerald-500 rounded-full")
            ui.label(title).classes(
                "text-sm font-bold font-mono tracking-[0.2em] text-white uppercase opacity-90"
            )

    # 3. Smooth Navigation Helper
    # This is the magic sauce. It plays the close animation BEFORE killing the page.
    async def smooth_navigate(target_url):
        left_drawer.hide()  # Trigger close animation
        await asyncio.sleep(
            0.1
        )  # Wait for animation (200ms is usually enough for the slide)
        ui.navigate.to(target_url)

    # 4. Drawer Content
    with left_drawer:
        with ui.column().classes("h-full w-full p-6 gap-1"):

            # --- BRANDING ---
            with ui.row().classes(
                "w-full items-center gap-3 mb-8 px-2 opacity-90 mt-2"
            ):
                ui.icon("hub", size="md", color="emerald-500").classes("animate-pulse")
                with ui.column().classes("gap-0"):
                    ui.label("LONGHAUL").classes(
                        "text-xl font-black tracking-tighter text-white leading-none"
                    )
                    ui.label("C2 FRAMEWORK").classes(
                        "text-[9px] font-mono text-emerald-500 tracking-[0.2em] leading-none"
                    )

            # --- NAVIGATION ---
            def nav_btn(label, icon, target):
                # Check if this is the active page (Simple string matching on title)
                # You might need to adjust mapping if 'title' doesn't exactly match the button label
                is_active = label.lower() in title.lower()

                # Active Styling vs Inactive Styling
                base_classes = "w-full rounded transition-all duration-300 font-mono text-xs tracking-wide px-4 py-3 border-l-2"

                if is_active:
                    style_classes = f"{base_classes} text-emerald-400 bg-white/5 border-emerald-500 font-bold"
                    icon_color = "emerald"
                else:
                    style_classes = f"{base_classes} text-neutral-400 hover:text-emerald-400 hover:bg-white/5 border-transparent hover:border-emerald-500"
                    icon_color = None  # Inherit

                ui.button(
                    label, icon=icon, on_click=lambda: smooth_navigate(target)
                ).props(
                    f"flat no-caps align=left color={icon_color if icon_color else 'grey'}"
                ).classes(
                    style_classes
                )

            # Render Buttons
            nav_btn("OPERATIONS", "precision_manufacturing", "/operations")
            nav_btn("PAYLOADS", "layers", "/payloads")
            nav_btn("LISTENERS", "rss_feed", "/listeners")
            nav_btn("SEARCH", "manage_search", "/search")
            nav_btn("SCRIPTS", "terminal", "/scripts")

            # --- FOOTER ---
            ui.space()

            with ui.column().classes("w-full gap-1 opacity-50 mb-2"):
                ui.separator().classes("bg-white/10 mb-2")
                # with ui.row().classes("w-full justify-between px-2"):
                #     ui.label("SYS_STATUS:").classes(
                #         "text-[9px] font-mono text-neutral-500"
                #     )
                #     ui.label("ONLINE").classes(
                #         "text-[9px] font-bold font-mono text-emerald-500"
                #     )
                ui.label("VER: BETA 0.0.1").classes(
                    "text-[12px] font-mono text-neutral-600 w-full text-center mt-1"
                )
