from nicegui import app, ui


async def navigate(destination: str, previous_uri: str = "/"):
    """
    Custom navigate hook that keep track of previous URI for backtracking purposes
    """
    app.storage.tab["previous_uri"] = previous_uri
    ui.navigate.to(destination)


async def get_current_uri() -> str:
    prev_uri = await ui.run_javascript("location.pathname")  # location.pathname -> current uri.

    if not prev_uri:
        prev_uri = "/"

    return prev_uri
