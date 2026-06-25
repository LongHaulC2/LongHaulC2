from nicegui import app, ui

from client.utils.helpers import notify


@ui.page("/logout")
def logout_page():
    # clear stored cookies
    app.storage.user["api_host"] = None
    ui.navigate.to("/login")
    notify("Logged out successfully")
