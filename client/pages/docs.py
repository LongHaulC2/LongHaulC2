from nicegui import ui

from client.info import EXTERNAL_DOC_ENDPOINT


@ui.page("/docs")
async def docs_page():
    ui.navigate.to(EXTERNAL_DOC_ENDPOINT, new_tab=True)
    ui.navigate.to("/operations")
