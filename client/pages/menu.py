import asyncio

from nicegui import app, ui

from client.info import VERSION_NUMBER

# F403, fine, lots of styles that could be imported from here
# this needs to be cleaned up in due time though, all styes are in the .css now
from client.style import *  # noqa: F403

from ..utils.checks import check_type


def setup_menu(title: str):
    # push user to login if no host is configured.
    # change to JWT once that is implemented
    # this is in menu because it's loaded into every page
    if not app.storage.user.get("api_host", ""):
        ui.navigate.to("/login")

    check_type(title, str, "title")

    # Drawer Setup
    # width=280: Standard width for tech consoles
    # behavior='mobile': Forces it to overlay content (smoother for this style)
    left_drawer = (
        ui.left_drawer(value=False, elevated=False, bordered=False)
        .props("width=280 behavior=mobile")
        .classes("bg-[#0F0F0F]")
    )

    # Header (Glassmorphism)
    with ui.header().classes("bg-black/40 backdrop-blur-md border-b border-white/5 h-16 row items-center px-4"):
        # Toggle Button
        ui.button(on_click=lambda: left_drawer.toggle(), icon="menu").props("flat dense square color=white").classes(
            "opacity-70 hover:opacity-100 transition-opacity"
        )

        # Page Title
        with ui.row().classes("items-center gap-2 ml-4"):
            ui.element("div").classes("w-1 h-4 bg-emerald-500 rounded-full")
            ui.label(title).classes("tech-label-header-bold")

    # Smooth Navigation Helper
    # This is the magic sauce. It plays the close animation BEFORE killing the page.
    async def smooth_navigate(target_url):
        left_drawer.hide()  # Trigger close animation
        await asyncio.sleep(0.1)  # Wait for animation (200ms is usually enough for the slide)
        ui.navigate.to(target_url)

    # Drawer Content
    with left_drawer:  # noqa: SIM117
        with ui.column().classes("h-full w-full p-6 gap-1"):
            # BRANDING
            with ui.row().classes("w-full items-center gap-3 mb-8 px-2 opacity-90 mt-2"):
                # ui.icon("hub", size="md", color="emerald-500").classes("animate-pulse")
                ui.image("/static/world_outline.png").classes(
                    "p-3 rounded-full bg-emerald-500/10 border border-emerald-500/20 w-12"
                ).classes("animate-pulse")
                with ui.column().classes("gap-0"):
                    ui.label("LONGHAUL").classes("tech-label-header")
                    ui.label("C2 FRAMEWORK").classes("tech-label-sub !text-emerald-500")

            # NAVIGATION
            def nav_btn(label, icon, target):
                # Check if this is the active page (Simple string matching on title)
                # You might need to adjust mapping if 'title' doesn't exactly match the button label
                is_active = label.lower() in title.lower()

                # Active Styling vs Inactive Styling
                # #noqa: E501, HTML style
                base_classes = (
                    "w-full rounded transition-all duration-300 font-mono text-xs tracking-wide px-4 py-3 border-l-2"  # noqa: E501
                )

                if is_active:
                    style_classes = f"{base_classes} text-emerald-400 bg-white/5 border-emerald-500 font-bold"
                    icon_color = "emerald"
                else:
                    # #noqa: E501, HTML style
                    style_classes = f"{base_classes} text-neutral-400 hover:text-emerald-400 hover:bg-white/5 border-transparent hover:border-emerald-500"  # noqa: E501
                    icon_color = None  # Inherit

                ui.button(label, icon=icon, on_click=lambda: smooth_navigate(target)).props(
                    f"flat no-caps align=left color={icon_color or 'grey'}"
                ).classes(style_classes)

            # Render Buttons
            ui.separator().classes("bg-white/5 mt-2 mb-2")
            ui.label("OPERATIONS").classes("tech-label-sub")
            nav_btn("OPERATIONS", "terminal", "/operations")
            nav_btn("ENGAGEMENT_MAP", "device_hub", "/graph")
            nav_btn("PAYLOADS", "layers", "/payloads")
            nav_btn("LISTENERS", "headphones", "/listeners")

            ui.separator().classes("bg-white/5 mt-4 mb-2")
            ui.label("RESOURCES").classes("tech-label-sub")
            nav_btn("DOCS", "info", "/docs")
            nav_btn("FILESTORE", "folder", "/filestore")
            nav_btn("PROFILES", "tune", "/profile-preview")

            ui.separator().classes("bg-white/5 mt-4 mb-2")
            ui.label("ADMIN").classes("tech-label-sub")
            nav_btn("STATUS", "arrow_circle_up", "/status")
            nav_btn("SETTINGS", "settings", "/settings")

            # FOOTER
            ui.space()
            nav_btn("DISCONNECT", "exit_to_app", "/logout")

            with ui.column().classes("w-full gap-1 opacity-50 mb-2"):
                ui.separator().classes("bg-white/10 mb-2")
                # with ui.row().classes("w-full justify-between px-2"):
                #     ui.label("SYS_STATUS:").classes(
                #         "text-[9px] font-mono text-neutral-500"
                #     )
                #     ui.label("ONLINE").classes(
                #         "text-[9px] font-bold font-mono text-emerald-500"
                #     )
                ui.label(f"LONGHAULC2 // {VERSION_NUMBER}").classes(
                    "text-[12px] font-mono text-neutral-600 w-full text-center mt-1"
                )
