from nicegui import app, ui


@ui.page("/logout")
def logout_page():
    # clear stored cookies
    app.storage.user["api_host"] = None
    ui.navigate.to("/login")
    ui.notify("Logged out successfully")
