from nicegui import ui


@ui.page("/admin/users")
async def admin_users_page():
    ui.navigate.to("/settings/users")
