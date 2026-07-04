from nicegui import ui


@ui.page("/profile")
async def profile_page():
    ui.navigate.to("/settings/profile")
